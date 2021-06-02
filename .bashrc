#~/.bashrc

if [ -f ./.env ]; then
    set -a
    . ./.env
    set +a
fi

e3lm() {
    python "$WORKSPACE/e3lm.py" $*
}

if [[ -f "$WORKSPACE/eutils.py" ]]; then
    eutils() {
        python "$WORKSPACE/eutils.py"
    }
fi

e3lm-benchmark() {
    python "$WORKSPACE/e3lm-benchmark.py" $*
}

alias pipu="python -m pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 python -m pip install -U"