import timeit
import sys
from e3lm.utils.lang import interpret

args = sys.argv
args.pop(0)

verbose = False
if "-v" in args:
    args.remove("-v")
    verbose = True

try:
    count = args.pop(0) if len(args) >= 1 else 100
    count = int(count)
except ValueError:
    count = 100
fname = args.pop(0) if len(args) >= 1 else "app.3lm"

def test():
    def get_text():
        with open(fname) as f:
            a = "".join(f.readlines())
        return (a + "\n") * count
    txt = get_text()
    b = interpret(txt)
    if verbose:
        print("  ", len(txt), "lines")
        print("  ", len(b.flat_blocks), "object(s)")
    return b


if __name__ == "__main__":
    if verbose:
        print(
            "Reading", "\"{}\"".format(fname),
            "content multiplied by", count, "..."
        )
    x = timeit.timeit(
        "test()",
        setup="from __main__ import test",
        number=1
    )
    print(x)
