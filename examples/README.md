# Examples

## mvp.py — end-to-end smoke test

Runs six steps against a real PPA or EPA device to verify the full client stack:

1. **Status** — reads device hostname, FLS state, initialisation flag, HTTPS flag, and timestamp.
2. **Check-in** — explicit backend check-in (also called implicitly by `ensure_ready`).
3. **Key creation** — generates an AES-256 key with label `mvp-example`.
4. **Encrypt** — AES-256-GCM encryption of 64 random bytes; prints ciphertext/IV/tag lengths.
5. **Decrypt** — round-trip decryption and equality assertion.
6. **Key deletion** — always runs in a `finally` block, even on failure, to avoid leaving keys behind.

Exit code 0 means all six steps passed. The key is always cleaned up regardless of outcome.

```bash
HEM_HOST=my.ence.do HEM_PASSPHRASE='your-passphrase' python examples/mvp.py
```

Expected output:

```
[1/6] status: hostname= fls_state=0 initialized=True https=False ts=2026-04-08T20:45:23Z
[2/6] checkin: OK
[3/6] created kid=8edce416d863052ffd9411ca86af1948
[4/6] encrypted: ciphertext=64B iv=16B tag=16B
[5/6] decrypt: round-trip OK
[6/6] deleted kid=8edce416d863052ffd9411ca86af1948
```

## wipe_keys.py — maintenance: wiping leaked test keys

Interrupted integration runs (Ctrl-C between create and `finally`) can leave
behind test keys on the device. This script inspects and removes them.

```bash
# Read-only inventory; protected device keys are tagged [PROTECTED]
HEM_HOST=my.ence.do HEM_PASSPHRASE='...' \
  uv run python examples/wipe_keys.py --list

# Dry-run: show what --all would remove without touching anything
HEM_HOST=my.ence.do HEM_PASSPHRASE='...' \
  uv run python examples/wipe_keys.py --all --dry-run

# Delete every key EXCEPT protected device keys (one bulk y/N prompt)
HEM_HOST=my.ence.do HEM_PASSPHRASE='...' \
  uv run python examples/wipe_keys.py --all

# Targeted cleanup of leaked test keys
HEM_HOST=my.ence.do HEM_PASSPHRASE='...' \
  uv run python examples/wipe_keys.py \
    --label-prefix it-page- --label-prefix it-get --label-prefix it-mvp
```

**Protected device keys.** `[PROTECTED]` is a `wipe_keys.py`-only concept — the HEM device and its API have no notion of protected keys. The script treats the following keys as protected
and refuses to touch them under `--all`:

- exact label `TLS PrivateKey` and `TLS Certificate` (the device's own TLS
  material — deleting these can render the device unreachable)
- any label containing `(Android)` or `(iPhone)`, case-insensitive (paired
  phones / external authenticators)

A protected key can only be deleted by passing its **exact** label via
`--label-prefix` and confirming a per-key prompt by typing the literal
string `YES`. `--yes` is ignored on this path by design. Partial-prefix
matches against a protected label print a warning and skip the key.
