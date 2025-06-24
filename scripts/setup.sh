#!/usr/bin/env bash
set -e

usage() {
    cat <<USAGE
Usage: $0 [OPTIONS]

Options:
  -e, --env PATH   Virtual environment location (default: .venv)
  --no-venv        Skip creating a virtual environment
  -d, --dev        Install development dependencies (pytest, pre-commit)
  -t, --test       Run tests after installation
  -h, --help       Show this help and exit
USAGE
}

ENV_PATH=".venv"
CREATE_VENV=1
INSTALL_DEV=0
RUN_TESTS=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -e|--env)
            ENV_PATH="$2"
            shift 2
            ;;
        --no-venv)
            CREATE_VENV=0
            shift
            ;;
        -d|--dev)
            INSTALL_DEV=1
            shift
            ;;
        -t|--test)
            RUN_TESTS=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
    shift
done

if [[ $CREATE_VENV -eq 1 ]]; then
    python -m venv "$ENV_PATH"
    # shellcheck disable=SC1090
    source "$ENV_PATH/bin/activate"
fi

pip install -e .
if [[ $INSTALL_DEV -eq 1 ]]; then
    pip install pytest pre-commit
    if command -v pre-commit >/dev/null 2>&1; then
        pre-commit install
    fi
fi

if [[ $RUN_TESTS -eq 1 ]]; then
    pytest -q
fi

echo "Setup complete"
