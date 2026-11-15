#!/usr/bin/env bash
set -euo pipefail

# Create venv
if [[ ! -d .venv ]]; then
    python3 -m venv .venv
fi

# Setup venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"

.venv/bin/pre-commit install

echo ""
echo "#=================================#"
echo "| Development setup successfully. |"
echo "#=================================#"
