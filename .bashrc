e3lm() {
    python "$WORKSPACE/e3lm.py" $*
}

if [[ -f "$WORKSPACE/eutils.py" ]]; then
    eutils() {
        python "$WORKSPACE/eutils.py"
    }
fi