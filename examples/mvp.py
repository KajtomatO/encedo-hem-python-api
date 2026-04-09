"""MVP test program for encedo-hem.

Runs the six steps from .ai/app-description.txt against a configured device.

Usage:
    HEM_HOST=my.ence.do HEM_PASSPHRASE='...' python examples/mvp.py
"""

from __future__ import annotations

import logging
import os
import secrets
import sys

from encedo_hem import CipherAlg, HemClient, HemError, KeyType


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    host = os.environ.get("HEM_HOST")
    passphrase = os.environ.get("HEM_PASSPHRASE")
    if not host or not passphrase:
        print("set HEM_HOST and HEM_PASSPHRASE", file=sys.stderr)
        return 2

    with HemClient(host=host, passphrase=passphrase) as hem:
        hem.ensure_ready()

        # 1. Print device status.
        status = hem.system.status()
        print(
            f"[1/6] status: hostname={status.hostname} "
            f"fls_state={status.fls_state} initialized={status.initialized} "
            f"https={status.https} ts={status.ts}"
        )

        # 2. Do a check-in (explicit, even if ensure_ready already ran one).
        hem.system.checkin()
        print("[2/6] checkin: OK")

        # 3. Create an example AES-256 key.
        kid = hem.keys.create(label="mvp-example", type=KeyType.AES256)
        print(f"[3/6] created kid={kid}")

        try:
            # 4. Encrypt a random message.
            plaintext = secrets.token_bytes(64)
            enc = hem.crypto.cipher.encrypt(kid, plaintext, alg=CipherAlg.AES256_GCM)
            assert enc.iv is not None and enc.tag is not None
            print(
                f"[4/6] encrypted: ciphertext={len(enc.ciphertext)}B "
                f"iv={len(enc.iv)}B tag={len(enc.tag)}B"
            )

            # 5. Decrypt and verify round-trip.
            recovered = hem.crypto.cipher.decrypt(
                kid,
                enc.ciphertext,
                alg=CipherAlg.AES256_GCM,
                iv=enc.iv,
                tag=enc.tag,
            )
            if recovered != plaintext:
                print("[5/6] decrypt: MISMATCH", file=sys.stderr)
                return 1
            print("[5/6] decrypt: round-trip OK")
        finally:
            # 6. Always remove the key, even on failure.
            try:
                hem.keys.delete(kid)
                print(f"[6/6] deleted kid={kid}")
            except HemError as exc:
                print(f"[6/6] delete failed: {exc}", file=sys.stderr)
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
