import pprint

COLORS = {
    "HEADER": '\033[95m',
    "INFO": '\033[94m',
    "SUCCESS": '\033[92m',
    "WARNING": '\033[93m',
    "ERROR": '\033[91m',
    "ENDC": '\033[0m',
    "BOLD": '\033[1m',
    "UNDERLINE": '\033[4m',
}

def _print(text, *args):  # pragma: no cover
    _all = [text, ]
    col = "ENDC"
    for i, arg in enumerate(args):
        if arg not in COLORS.keys():
            _all.append(arg)
        else:
            col = arg

    cprint(*_all, col=col)


def cprint(text, col="INFO"):  # pragma: no cover
    col = col.upper()
    print(COLORS[col] + str(text) + COLORS["ENDC"])


def nprint(node, lvl=0, func=cprint):  # pragma: no cover
    if node == None:
        func(" - "*lvl + "None")
    elif type(node) != str:
        if lvl == 0:
            func(" - "*lvl + str(node), "BOLD")
        else:
            func(" - "*lvl + str(node), "INFO")

        children = []
        if hasattr(node, "children"):
            children = node.children
        elif hasattr(node, "blocks"):
            children = node.blocks

        if children:
            for child in children:
                if lvl > 5:
                    break
                nprint(child, lvl+1, func=func)
    else:
        func(" - "*lvl + str(node), "SUCCESS")
