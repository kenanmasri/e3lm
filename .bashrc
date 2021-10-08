#~/.bashrc

# For environment development (using VSCode)
if [ -f ./.env ]; then
    set -a
    . ./.env
    set +a
fi

# For source debugging purposes
e3lmcli() {
    python "$WORKSPACE/src/cli.py" $*
}

# Activate the VENV optionally.
if [[ "$ACTIVATE_VENV" != "false" && "$ACTIVATE_VENV" != "False" ]]; then
    source "$VENV/Scripts/activate"
fi