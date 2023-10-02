#!/usr/bin/env bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly MAIN_PY="${SCRIPT_DIR}/client_app.py"
readonly PYTHON_INTERPRETER="$(which python3)"

"${PYTHON_INTERPRETER}" "${MAIN_PY}"
