# -*- coding: utf-8 -*-

from asciitree import LeftAligned, Traversal, KeyArgsConstructor
from asciitree.drawing import BoxStyle

COLORS = {
    # Default...
    "NONE": u"",
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
    # From CLI...
    "H": u'\x1b[95m',  # HEADER
    "1": u'\x1b[38;5;164m',  # FIRST
    "2": u'\x1b[38;5;173m',  # SECOND
    "3": u'\x1b[38;5;177m',  # THIRD
    "4": u'\x1b[38;5;225m',  # FOURTH
    "E": u'\x1b[91m',  # ERROR
    "W": u'\x1b[93m',  # WHITE
    "R": u'\x1b[0m',  # RESET
    "B": u'\x1b[1m',  # BOLD
    "U": u'\x1b[4m',  # UNDERLINE

    "RESET": u'\x1b[0m',
    "GRAY": u'\x1b[38;5;245m',

    "A": u'\x1b[38;5;164m',  # A
    "B": u'\x1b[38;5;173m',  # B
    "C": u'\x1b[38;5;177m',  # C
    "D": u'\x1b[38;5;225m',  # D
    "E": u'\x1b[95m',        # E
    "LOG": u'\x1b[38;5;164m',  # LOGGING TAG
    "LOG_MSG": u'\x1b[38;5;245m',  # LOGGING MESSAGE
    "ERROR": u'\x1b[91m',  # ERROR
}


class TraverseArrow(KeyArgsConstructor):
    pass


class TraverseItem(KeyArgsConstructor):
    pass


class TRAVERSE(Traversal):
    evaluate = False
    program_name = ""

    def __init__(self, cols=COLORS, charset=[], **kwargs):
        self.charset = {
            "Program": chr(4),
            "Block": "□ ",
            "TraverseItem": {
                "Import": " ╰ ",
                "Attr": "⌐ ",
                "TraverseArrow": "→",
                "tokens": "←",
            },
        } if charset == [] else charset
        self.COLS = cols
        super().__init__(**kwargs) # Pass kwargs to parent


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
        namae = self.COLS["HEADER"] + self.program_name # or node.id
        return self.COLS["BOLD"] + self.COLS["INFO2"] + " " + self.charset["Program"] + " " + self.COLS["INFO"] + "Program(" + namae + self.COLS["INFO"] + ")" + self.COLS["R"]

    def get_text_of_Block(self, block):
        idpart = (self.COLS["HEADER"] + self.COLS["UNDERLINE"] +
                  f"#{block.id}" + self.COLS["R"]) if hasattr(block, "id") else ""
        namepart = (self.COLS["HEADER"] + ", " + block.name +
                    self.COLS["R"]) if block.name != "" else ""
        namae = self.COLS["HEADER"] + block.type + idpart + namepart
        return self.COLS["INFO2"]+ self.charset["Block"] + self.COLS["INFO"] + "Block(" + namae + self.COLS["INFO"] + ")" + self.COLS["R"]

    def get_text_of_TraverseItem(self, item):
        if item.type == "Import":
            return self.COLS["INFO2"] + self.charset["TraverseItem"]["Import"] + self.COLS["GRAY"] + "import " + self.COLS["WHITE"] + item.value + self.COLS["R"]
        elif item.type == "Attr":
            attr = item
            namae = self.COLS["HEADER"] + attr.name + self.COLS["R"]
            eqq = self.COLS["SUCCESS"] + " = " + self.COLS["R"]
            valae = self.COLS["INFO"] + str(attr.value.value) + self.COLS["R"]
            arrowpart = ""
            if type(attr.children) == TraverseArrow:
                arrowpart = " " + \
                    self.COLS["WARNING"] + \
                    "".join([str(" " + self.COLS["BLUE"] + self.charset["TraverseItem"]["TraverseArrow"] + self.COLS["CYAN"] +
                            " %s") % v for v in attr.children.rights])
            if attr.name == "body":
                if hasattr(attr.o.body, "tokens"):
                    valae = self.COLS["HEADER"] + attr.value[:5] + \
                        (attr.value[5:] and "...") + \
                        "["+len(attr.value)+"]" + self.COLS["R"]
                    # attr.o.body.tokens
                    arrowpart = " " + \
                        self.COLS["WARNING"] + \
                        " " + self.charset["TraverseItem"]["tokens"] + "(" + ",".join(attr.o.body.tokens) + ")"
            return self.COLS["INFO2"] + self.charset["TraverseItem"]["Attr"] + self.COLS["SUCCESS"] + "Attr(" + namae + eqq + valae + self.COLS["SUCCESS"] + ")" + arrowpart + self.COLS["R"]

    def get_text_of_TraverseArrow(self, arrow):
        return str(arrow.value)


TREE = LeftAligned


def TREEBOX_E3LM(colorname, charset=[]):
    """Return a BoxStyle for asciitree using ordered charset and named color"""
    if charset == []:
        # chr(0x2514), chr(0x2500), chr(0x2502), chr(0x251C)]
        charset = ["└", "─", "│", "├"]

    if colorname == "NONE":
        box = {
            'UP_AND_RIGHT': charset[0],
            'HORIZONTAL': charset[1],
            'VERTICAL': charset[2],
            'VERTICAL_AND_RIGHT': charset[3],
        }
    else:
        box = {
            'UP_AND_RIGHT': COLORS[colorname] + charset[0] + COLORS["R"],
            'HORIZONTAL': COLORS[colorname] + charset[1] + COLORS["R"],
            'VERTICAL': COLORS[colorname] + charset[2] + COLORS["R"],
            'VERTICAL_AND_RIGHT': COLORS[colorname] + charset[3] + COLORS["R"],
        }
    return box


class BOXSTYLE(BoxStyle):
    """A rendering style that uses box draw characters and a common layout."""
    gfx = None        #: Glyphs to use.
    color = "NONE"    #: Color to use for tree arrows.
    label_space = 1   #: Space between glyphs and label.
    horiz_len = 2     #: Length of horizontal lines
    indent = 1        #: Indent for subtrees
    label_format = u'{}'

    def __init__(self, color="NONE", gfx=TREEBOX_E3LM, charset=[]):
        self.color = color
        self.gfx = gfx(color, charset)

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


TREE_NODES = TREE(draw=BOXSTYLE(color="INFO2", gfx=TREEBOX_E3LM, charset=[]))
TREE_NODES_NC = TREE(draw=BOXSTYLE(color="NONE", gfx=TREEBOX_E3LM, charset=[]))
TREE_NODES_NG = TREE(draw=BOXSTYLE(
    color="INFO2", gfx=TREEBOX_E3LM, charset=["'->", "-", "|", "|->"]))
TREE_NODES_NCNG = TREE(draw=BOXSTYLE(
    color="NONE", gfx=TREEBOX_E3LM, charset=["'->", "-", "|", "|->"]))


def _print(text, *args):  # pragma: no cover
    _all = [str(text), ]
    col = "ENDC"
    for i, arg in enumerate(args):
        if arg not in COLORS.keys():
            _all.append(str(arg))
        else:
            col = arg

    cprint("\n".join(_all), color=col)


def cprint(text, color="NONE"):  # pragma: no cover
    if color == "NONE" or color == "":
        print(str(text))
    else:
        color = color.upper()
        print(COLORS[color] + str(text) + COLORS["ENDC"])


def nprint(node, max_level=6, treefunc=TREE_NODES, **kwargs):  # pragma: no cover
    """Print nodes using `asciitree`"""

    if "noglyph" in kwargs.keys():
        if kwargs["noglyph"] == True:
            traverse_charset = {
                "Program": "*",
                "Block": "o ",
                "TraverseItem": {
                    "Import": " < ",
                    "Attr": "> ",
                    "TraverseArrow": "=>",
                    "tokens": "<=",
                }
            }

            if treefunc == TREE_NODES:
                treefunc = TREE_NODES_NG
            elif treefunc == TREE_NODES_NC:
                treefunc = TREE_NODES_NCNG
        else:
            traverse_charset = []
    else:
        traverse_charset = []

    if "pallete" in kwargs.keys():
        if kwargs["pallete"] == None:
            pallete = {k: "" for k in COLORS.keys()}

            if treefunc == TREE_NODES:
                treefunc = TREE_NODES_NC
            elif treefunc == TREE_NODES_NG:
                treefunc = TREE_NODES_NCNG
        else:
            pallete = kwargs["pallete"]
    else:
        pallete = COLORS

    treefunc.traverse = TRAVERSE(cols=pallete, charset=traverse_charset, **kwargs)
    print("\n" + treefunc(node) + "\n")
