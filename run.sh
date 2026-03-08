set -e
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
python -m asag_engine.api.app