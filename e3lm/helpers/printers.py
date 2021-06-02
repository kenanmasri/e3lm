# -*- coding=utf-8 -*-

import pprint
from asciitree import LeftAligned, Traversal, KeyArgsConstructor
from asciitree.drawing import BoxStyle

COLORS = {
    # Default...
    "GRAY": u'\x1b[38;5;245m',
    "HEADER": u'\x1b[95m',
    "INFO": u'\x1b[38;5;164m',
    "INFO2": u'\x1b[38;5;172m',
    "SUCCESS": u'\x1b[38;5;173m',
    "WARNING": u'\x1b[93m',
    "BLACK": u'\x1b[30m',
    "RED": u'\x1b[31m',
    "GREEN": u'\x1b[32m',
    "GREEN": u'\x1b[32m',
    "YELLOW": u'\x1b[33m',
    "BLUE": u'\x1b[34m',
    "MAGENTA": u'\x1b[35m',
    "CYAN": u'\x1b[36m',
    "WHITE": u'\x1b[37m',
    "DEFAULT": u'\x1b[39m',
    "CYAN": u'\x1b[36m',
    "BOLD": u'\x1b[1m',
    "ITALICS": u'\x1b[3m',
    "UNDERLINE": u'\x1b[4m',
    "STRIKE": u'\x1b[9m',
    "ENDC": u'\x1b[0m',
    "R": u'\x1b[0m',
    "RESET": u'\x1b[0m',
    # From CLI...
    "H": u'\x1b[95m', # HEADER
    "1": u'\x1b[38;5;164m', # FIRST
    "2": u'\x1b[38;5;173m', # SECOND
    "3": u'\x1b[38;5;177m', # THIRD
    "4": u'\x1b[38;5;225m', # FOURTH
    "E": u'\x1b[91m', # ERROR
    "W": u'\x1b[93m', # WHITE
    "R": u'\x1b[0m', # RESET
    "B": u'\x1b[1m', # BOLD
    "U": u'\x1b[4m', # UNDERLINE
}


class TraverseArrow(KeyArgsConstructor):
    pass


class TraverseItem(KeyArgsConstructor):
    pass


class TRAVERSE(Traversal):
    evaluate = False
    colors_enabled = True
    program_name = ""

    def get_children(self, node):
        """Return a list of children of a node."""
        method = 'get_children_of_{}'.format(type(node).__name__)
        getter = getattr(self, method, None)
        if getter != None:
            result = getter(node)
            return result
        return []

    # Program node children
    def get_children_of_Program(self, node):
        imports = [TraverseItem(type="Import", value=x) for x in node.imports]
        return [*imports, *node.blocks]

    # Block node children (blocks + attrs + body)
    def get_children_of_Block(self, block):
        c = [
            *block.children,
            *[TraverseItem(type="Attr", name=a, o=block, value=b, children=self.get_children(b))
              for a, b in block._attrs.items() if a != "body"],
        ]
        if hasattr(block, "body"):
            c.append(TraverseItem(type="Attr", name="body",
                     o=block, value=block._attrs["body"]))
        return c

    # Attr children (as arrows holder)
    def get_children_of_Attr(self, attr):
        if self.evaluate:
            if hasattr(attr, "eval"):
                return TraverseArrow(left=attr.value, rights=[
                    f"\"{attr.eval}\"" if type(attr.eval) == str else attr.eval
                ])
        return [attr.value]

    # Placeholder
    def get_children_of_TraverseArrow(self, traverse_arrow):
        return [*traverse_arrow.rights]

    # Placeholder
    def get_children_of_TraverseItem(self, traverse_item):
        return []

    def get_root(self, tree):
        """Return a node representing the tree root from the tree."""
        return tree

    def get_text(self, node):
        """Return the text associated with a node."""
        method = 'get_text_of_{}'.format(type(node).__name__)
        getter = getattr(self, method, None)
        if getter != None:
            result = getter(node)
            return result
        return str(node)

    def get_text_of_Program(self, node):
        namae = COLORS["HEADER"] + self.program_name or node.id
        return COLORS["BOLD"] + COLORS["INFO2"] + " "+chr(4)+" " + COLORS["INFO"] + "Program(" + namae + COLORS["INFO"] + ")" + COLORS["R"]

    def get_text_of_Block(self, block):
        idpart = (COLORS["HEADER"] + COLORS["UNDERLINE"] +
                  f"#{block.id}" + COLORS["R"]) if hasattr(block, "id") else ""
        namepart = (COLORS["HEADER"] + ", " + block.name +
                    COLORS["R"]) if block.name != "" else ""
        namae = COLORS["HEADER"] + block.type + idpart + namepart
        return COLORS["INFO2"] + "□ " + COLORS["INFO"] + "Block(" + namae + COLORS["INFO"] + ")" + COLORS["R"]

    def get_text_of_TraverseItem(self, item):
        if item.type == "Import":
            return COLORS["INFO2"] + " ╰ " + COLORS["GRAY"] + "import " + COLORS["WHITE"] + item.value + COLORS["R"]
        elif item.type == "Attr":
            attr = item
            namae = COLORS["HEADER"] + attr.name + COLORS["R"]
            eqq = COLORS["SUCCESS"] + " = " + COLORS["R"]
            valae = COLORS["INFO"] + str(attr.value.value) + COLORS["R"]
            arrowpart = ""
            if type(attr.children) == TraverseArrow:
                arrowpart = " " + \
                    COLORS["WARNING"] + \
                    "".join([str(" " + COLORS["BLUE"] + "→" + COLORS["CYAN"] +
                            " %s") % v for v in attr.children.rights])
            if attr.name == "body":
                if hasattr(attr.o.body, "body_tokens"):
                    valae = COLORS["HEADER"] + attr.value[:5] + \
                        (attr.value[5:] and "...") + \
                        "["+len(attr.value)+"]" + COLORS["R"]
                    # attr.o.body.body_tokens
                    arrowpart = " " + \
                        COLORS["WARNING"] + \
                        " ← (" + ",".join(attr.o.body.body_tokens) + ")"
            return COLORS["INFO2"] + "⌐ " + COLORS["SUCCESS"] + "Attr(" + namae + eqq + valae + COLORS["SUCCESS"] + ")" + arrowpart + COLORS["R"]

    def get_text_of_TraverseArrow(self, arrow):
        return str(arrow.value)


TREE = LeftAligned


def TREEBOX_E3LM(colorname, charset=[]):
    """Return a BoxStyle for asciitree using ordered charset and named color"""
    if charset == []:
        charset = [chr(0x2514), chr(0x2500), chr(0x2502), chr(0x251C)]
    box = {
        'UP_AND_RIGHT': COLORS[colorname] + charset[0] + COLORS["R"],
        'HORIZONTAL': COLORS[colorname] + charset[1] + COLORS["R"],
        'VERTICAL': COLORS[colorname] + charset[2] + COLORS["R"],
        'VERTICAL_AND_RIGHT': COLORS[colorname] + charset[3] + COLORS["R"],
    }
    return box


class BOXSTYLE(BoxStyle):
    """A rendering style that uses box draw characters and a common layout."""
    gfx = TREEBOX_E3LM("INFO2")  # : Glyphs to use.
    label_space = 1   #: Space between glyphs and label.
    horiz_len = 2     #: Length of horizontal lines
    indent = 1        #: Indent for subtrees
    label_format = u'{}'

    def child_head(self, label):
        return (' ' * self.indent
                + self.gfx['VERTICAL_AND_RIGHT']
                + self.gfx['HORIZONTAL'] * self.horiz_len
                + ' ' * self.label_space
                + label)

    def child_tail(self, line):
        return (' ' * self.indent
                + self.gfx['VERTICAL']
                + ' ' * self.horiz_len
                + line)

    def last_child_head(self, label):
        return (' ' * self.indent
                + self.gfx['UP_AND_RIGHT']
                + self.gfx['HORIZONTAL'] * self.horiz_len
                + ' ' * self.label_space
                + label)

    def last_child_tail(self, line):
        return (' ' * self.indent
                # + ' ' * len(self.gfx['VERTICAL'])
                + ' ' * self.horiz_len
                + line)


TREE_NODES = TREE(draw=BOXSTYLE())


def _print(text, *args):  # pragma: no cover
    _all = [text, ]
    col = "ENDC"
    for i, arg in enumerate(args):
        if arg not in COLORS.keys():
            _all.append(arg)
        else:
            col = arg

    cprint("\n".join(_all), col=col)


def cprint(text, col="INFO"):  # pragma: no cover
    col = col.upper()
    print(COLORS[col] + str(text) + COLORS["ENDC"])


def nprint(node, max_level=6, treefunc=TREE_NODES, **kwargs):  # pragma: no cover
    """Print nodes using `asciitree`"""
    treefunc.traverse = TRAVERSE(**kwargs)
    print("\n" + treefunc(node) + "\n")
