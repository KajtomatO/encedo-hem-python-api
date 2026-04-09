"""List or delete keys on a HEM device.

DANGEROUS — this script removes keys from the device. Use it to clean up
after interrupted integration runs that leaked keys (typically labels
starting with ``it-page-``, ``it-get``, ``it-mvp``, ``mvp-example``).

A small set of keys is treated as **protected device keys**:

- ``TLS PrivateKey`` and ``TLS Certificate`` (the device's own TLS material)
- any key whose label contains ``(Android)`` or ``(iPhone)`` — paired phones
  / external authenticators (case-insensitive match)

Protected keys are excluded from ``--all``. They can only be deleted by
naming their **exact** label via ``--label-prefix`` and confirming each one
interactively. ``--yes`` is ignored for protected keys — every protected
deletion requires a fresh per-key ``YES`` confirmation, by design.

Usage:
    HEM_HOST=my.ence.do HEM_PASSPHRASE='...' python examples/wipe_keys.py [OPTIONS]

Options:
    --list                  List every key on the device and exit. Read-only.
    --all                   Delete every key on the device EXCEPT protected
                            device keys. Mutually exclusive with --label-prefix.
    --label-prefix PREFIX   Delete keys whose label starts with PREFIX.
                            Repeatable. Required (with a value) when neither
                            --list nor --all is used. A protected key is only
                            deleted if some PREFIX equals its label exactly;
                            partial (startswith-only) hits are skipped with a
                            warning.
    --dry-run               Print what would happen, do nothing.
    --yes                   Skip the bulk confirmation for non-protected keys.
                            Has no effect on protected keys.

Exit codes:
    0  success (or dry-run, or list)
    1  user aborted, or one or more deletes failed
    2  bad usage / missing environment
"""

from __future__ import annotations

import argparse
import os
import sys

from encedo_hem import HemClient, HemError
from encedo_hem.models import KeyInfo

_PROTECTED_LABELS: frozenset[str] = frozenset({"TLS PrivateKey", "TLS Certificate"})
"""Exact labels that are always treated as device-internal keys (TLS material)."""

_PROTECTED_LABEL_SUBSTRINGS: tuple[str, ...] = ("(android)", "(iphone)")
"""Case-insensitive label substrings that mark a paired-phone key. Identifying
phones by label rather than by key algorithm is the spec choice — the same
algorithm may legitimately be used for non-protected keys."""


def _is_protected(key: KeyInfo) -> bool:
    if key.label in _PROTECTED_LABELS:
        return True
    label_lower = key.label.lower()
    return any(s in label_lower for s in _PROTECTED_LABEL_SUBSTRINGS)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List or delete keys on a HEM device. Deletion is destructive.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list every key on the device and exit (read-only)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--all",
        action="store_true",
        help="delete every key EXCEPT protected device keys",
    )
    mode.add_argument(
        "--label-prefix",
        action="append",
        default=[],
        metavar="PREFIX",
        help="delete keys whose label starts with PREFIX (repeatable). "
        "Protected keys require an exact label match and per-key confirmation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list matching keys without deleting them",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the bulk confirmation prompt (ignored for protected keys)",
    )
    return parser.parse_args()


def _print_keys(keys: list[KeyInfo], indent: str = "  ", *, mark_protected: bool = False) -> None:
    for key in keys:
        tag = "  [PROTECTED]" if mark_protected and _is_protected(key) else ""
        print(f"{indent}{key.kid}  {key.label!r}  ({key.type.algorithm}){tag}")


def _confirm_protected(key: KeyInfo) -> bool:
    """Strict per-key confirmation for protected device keys.

    Requires the user to type the literal string ``YES`` (uppercase). Any
    other input — including ``y``, ``yes``, blank, EOF — aborts. ``--yes``
    on the command line never reaches this function; protected deletes
    must always pass through here.
    """
    print(
        f"\nABOUT TO DELETE PROTECTED DEVICE KEY:\n"
        f"  kid:   {key.kid}\n"
        f"  label: {key.label!r}\n"
        f"  type:  {key.type.algorithm}\n"
        f"This may render the device unreachable or break phone pairing."
    )
    try:
        answer = input("type 'YES' (uppercase) to confirm, anything else aborts: ")
    except EOFError:
        return False
    return answer == "YES"


def main() -> int:
    args = _parse_args()

    host = os.environ.get("HEM_HOST")
    passphrase = os.environ.get("HEM_PASSPHRASE")
    if not host or not passphrase:
        print("set HEM_HOST and HEM_PASSPHRASE", file=sys.stderr)
        return 2

    if not (args.list or args.all or args.label_prefix):
        print(
            "nothing to do: pass --list, --all, or one or more --label-prefix PREFIX",
            file=sys.stderr,
        )
        return 2

    with HemClient(host=host, passphrase=passphrase) as hem:
        hem.ensure_ready()

        all_keys = list(hem.keys.list())

        # --- read-only branch ---
        if args.list:
            protected_count = sum(1 for k in all_keys if _is_protected(k))
            print(f"device {host!r}: {len(all_keys)} key(s) ({protected_count} protected)")
            _print_keys(all_keys, mark_protected=True)
            return 0

        # --- partition into regular targets, protected targets, partial-hit warnings ---
        regular_targets: list[KeyInfo] = []
        protected_targets: list[KeyInfo] = []
        partial_protected: list[KeyInfo] = []  # protected keys whose prefix only partially matched

        if args.all:
            scope_desc = "ALL keys (excluding protected device keys)"
            for key in all_keys:
                if _is_protected(key):
                    continue  # silently excluded under --all per spec
                regular_targets.append(key)
        else:
            prefixes: list[str] = args.label_prefix
            scope_desc = f"keys matching label prefix(es) {prefixes!r}"
            for key in all_keys:
                hits = [p for p in prefixes if key.label.startswith(p)]
                if not hits:
                    continue
                if _is_protected(key):
                    if any(p == key.label for p in hits):
                        protected_targets.append(key)
                    else:
                        partial_protected.append(key)
                else:
                    regular_targets.append(key)

        print(
            f"device {host!r}: {len(all_keys)} key(s) total — {scope_desc}\n"
            f"  regular targets:   {len(regular_targets)}\n"
            f"  protected targets: {len(protected_targets)}  (require per-key confirmation)\n"
            f"  protected skipped: {len(partial_protected)}  (partial-match only)"
        )

        if partial_protected:
            print("\nWARNING: the following PROTECTED device keys partially match a")
            print("prefix but will be SKIPPED. To remove one of these, re-run with")
            print("--label-prefix set to its EXACT label:")
            _print_keys(partial_protected, indent="  ! ")

        if regular_targets:
            print("\nregular keys to delete:")
            _print_keys(regular_targets)

        if protected_targets:
            print("\nPROTECTED device keys queued for deletion (per-key confirmation):")
            _print_keys(protected_targets, indent="  * ")

        if not regular_targets and not protected_targets:
            print("\nnothing to do")
            return 0

        if args.dry_run:
            print("\ndry-run: no keys deleted")
            return 0

        # --- regular deletions: bulk confirmation, --yes can skip ---
        regular_failures = 0
        if regular_targets:
            if not args.yes:
                answer = (
                    input(f"\ndelete {len(regular_targets)} regular key(s)? [y/N] ").strip().lower()
                )
                if answer != "y":
                    print("aborted regular deletion")
                    if not protected_targets:
                        return 1
                    regular_targets = []  # fall through to protected handling

            for key in regular_targets:
                try:
                    hem.keys.delete(key.kid)
                    print(f"deleted {key.kid}  {key.label!r}")
                except HemError as exc:
                    regular_failures += 1
                    print(
                        f"FAILED  {key.kid}  {key.label!r}: {exc}",
                        file=sys.stderr,
                    )

        # --- protected deletions: ALWAYS interactive, --yes ignored ---
        protected_failures = 0
        protected_aborted = 0
        for key in protected_targets:
            if not _confirm_protected(key):
                protected_aborted += 1
                print(f"skipped {key.kid}  {key.label!r}")
                continue
            try:
                hem.keys.delete(key.kid)
                print(f"deleted PROTECTED {key.kid}  {key.label!r}")
            except HemError as exc:
                protected_failures += 1
                print(
                    f"FAILED  PROTECTED {key.kid}  {key.label!r}: {exc}",
                    file=sys.stderr,
                )

        deleted_total = (
            len(regular_targets)
            - regular_failures
            + len(protected_targets)
            - protected_failures
            - protected_aborted
        )
        print(
            f"\ndone: {deleted_total} deleted, "
            f"{regular_failures + protected_failures} failed, "
            f"{protected_aborted} protected skipped"
        )
        return 1 if (regular_failures or protected_failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
