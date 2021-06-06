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

alias pip-update-all="python -m pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 python -m pip install -U"