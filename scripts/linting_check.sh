#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK=0

for arg in "$@"; do
    case "$arg" in
        --hook) HOOK=1 ;;
        *) echo "Unknown argument: $arg" >&2; exit 2 ;;
    esac
done

fail() {
    echo -e "\e[31mLinting failed.\e[0m Run manually to see details:" >&2
    echo "  $ROOT/scripts/linting_check.sh" >&2
    exit 1
}

if [ "$HOOK" -eq 1 ]; then
    uv run --project "$ROOT" ruff check "$ROOT" -q       || fail
    uv run --project "$ROOT" ruff format --check "$ROOT" -q || fail
    uv run --project "$ROOT" mypy --strict "$ROOT/src" >/dev/null || fail
else
    echo "==> Linting check..."
    uv run --project "$ROOT" ruff check "$ROOT"          || fail

    echo "==> Formatting check..."
    uv run --project "$ROOT" ruff format --check "$ROOT" || fail

    echo "==> Type check..."
    uv run --project "$ROOT" mypy --strict "$ROOT/src"   || fail

    echo -e "==> All checks \e[32mpassed\e[0m."
fi
