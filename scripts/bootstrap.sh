#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Install uv if not already present.
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Syncing dependencies (including dev extras)..."
uv sync --project "$ROOT" --extra dev

echo "Installing git hooks..."
git -C "$ROOT" config core.hooksPath .githooks

echo "Done. Run 'uv run pytest -q' to execute tests."
