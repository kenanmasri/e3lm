"""
Author: Kenan Masri

"""
import json
from copy import deepcopy
from e3lm.lang.data import basic_dt
from e3lm.helpers.printers import cprint


class AST:
    """Base AST node."""

    def __init__(self, children=[]):
        self.children = children

    def add(self, ast):
        self.children.append(ast)
        return self

    def __str__(self):
        _parts = ", "
        if hasattr(self, "id"):
            _parts += str(self.id) + ", "
        if hasattr(self, "value"):
            _parts += "value=" + str(self.value) + ", "
        _parts = _parts[:-2]

        if _parts != "":
            return f"AST({self.__class__.__name__}, {_parts})"
        return f"AST({self.__class__.__name__})"

    __repr__ = __str__


class Program(AST):
    """A program that contains `blocks`."""

    def __init__(self, imports=[], blocks=[], **kwargs):
        self.imports = imports
        # Attribute "blocks" is added after first pre-interpretation.
        # It refers to current interpreter blocks array.
        self.blocks = blocks
        self.flat_blocks = kwargs['flat_blocks'] \
            if 'flat_blocks' in kwargs.keys() else []

    def build_flat(self):
        """Build the `flat_blocks` from `self.blocks`"""
        def append(b):
            x = []
            for _b in b:
                if len(_b.children) > 0:
                    x.extend(append(_b.children))
                x.append(_b)
            return x

        self.flat_blocks = append(self.blocks)

    def add(self, block):
        self.blocks.append(block)
        return self

    def block_by_name(self, name):
        for a in self.flat_blocks:
            if a.name == name:
                return a
        return None

    def __str__(self):
        return f"Program({self.id})" if hasattr(self, "id") else "Program()"

    __repr__ = __str__


class Block(AST):
    """Block that contains `children` blocks and `attrs`."""

    def __init__(self, klass=None, children=[], attrs={}, name=""):
        self.type = klass
        self._attrs = attrs
        self.name = name
        self.children = children if children != None else []
        if type(children) == BlockContent:
            self.children = [a for a in children.children if type(a) == Block]
            self._attrs = {a.name: a
                           for a in children.children if type(a) == Attr}

    def __str__(self):
        idpart = f"#{self.id}" if hasattr(self, "id") else ""

        if hasattr(self, "name") and self.name != "":
            return f"Block({self.type}{idpart}, {self.name})"
        else:
            return f"Block({self.type}{idpart})"

    __repr__ = __str__


class Lazy(AST):
    """Lazy placeholder."""
    pass


class BlockContent(AST):
    """BlockContent Placeholder for parsing."""

    def __init__(self, children):
        self.children = children


class Attr(AST):
    """Attribute for `Block` object."""

    def __init__(self, name, value, **kwargs):
        self.name = name
        self.value = value
        if self.name == "body":
            if "tokens" in kwargs.keys():
                self.tokens = kwargs["tokens"] or []

    def __str__(self):
        return f"Attr({self.name}={self.value})"

    __repr__ = __str__


class BinOp(AST):
    def __init__(self, op, left=None, right=None):
        self.token = self.op = op
        self.left = left
        self.right = right

    def __str__(self):
        return f"BinOp({str(self.left)} {self.op} {str(self.right)})"

    __repr__ = __str__


class UnaryOp(AST):
    def __init__(self, op, value):
        self.token = self.op = op
        self.value = value

    def __str__(self):
        return f"UnaryOp({self.op} {str(self.value)})"

    __repr__ = __str__


class Num(AST):
    """Number object with `value` and `type` `value` is the representation of
    the number, while `eval` is the actual value.

    Available types:     NUM_INT     NUM_FLOAT     NUM_HEX     NUM_OCT
    NUM_IMAG
    """

    def __init__(self, value, type="NUM_INT"):
        self.value = value
        self.type = type

    def __str__(self):
        return f"Num({self.value})"

    __repr__ = __str__


class Str(AST):
    """String object with `value` and `type`

    Available types:     SINGLEQ1     SINGLEQ2     TRIPLEQ1     TRIPLEQ2
    """

    def __init__(self, value):
        self.value = value
        self.type = "SINGLEQ1"

    def __str__(self):
        return f"Str({self.value})"

    __repr__ = __str__


class Bool(AST):
    def __init__(self, value):
        self.value = True if value.lower() == "true" else False

    def __str__(self):
        return "Bool(" + ("true" if self.value else "false") + ")"

    __repr__ = __str__


class Undefined(AST):
    def __init__(self, value=None):
        self.value = value

    def __str__(self):
        return "None()"


class Array(AST):
    def __str__(self):
        return f"[.{len(self.children)}.]"

    __repr__ = __str__


class Index(AST):
    """Index of an array or dict."""

    def __init__(self, value=None):
        self.value = value

    def __str__(self):
        return "[{}]".format(self.value)

    __repr__ = __str__


class DictData(AST):
    """Dictionary data placeholder for parsing."""

    def __init__(self, children=[]):
        self.children = children

    def __str__(self):
        return "DictData("+str(len(self.children))+")"

    __repr__ = __str__


class Dict(AST):
    """Dict object containing `DictCouple` children."""

    def __init__(self, dictdata):
        self.children = dictdata.children

    def __str__(self):
        return "{." + str(len(self.children)) + ".}"

    __repr__ = __str__


class DictCouple(AST):
    """A dict couple in the form: `left: right`."""

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return f"DictCouple({self.left} -> {self.right})"

    __repr__ = __str__


class Func(AST):
    """Function with `value` as its name, `children` as arguments."""

    def __init__(self, func, *args, **kwargs):
        self.value = func
        self.children = []
        if len(args) > 1:
            self.children = args
        elif len(args) == 1:
            if isinstance(args[0], list):
                self.children = args[0]
            elif isinstance(args[0], FuncArgs):
                self.children = args[0].children
            else:
                self.children = [args[0]]

    def __str__(self):
        if self.children:
            return f"{self.value}(.{len(self.children)}.)"
        return f"{self.value}()"

    __repr__ = __str__


class FuncArgs(AST):
    """Function arguments placeholder for parsing."""

    def __len__(self):
        return len(self.children)

    def __str__(self):
        return f"Args({self.__len__()})"

    __repr__ = __str__


class Identifier(AST):
    """An expression with multiple AST nodes.

    `children` are in ltr order.
    """

    def __init__(self, children=[]):
        self.children = []
        for i, child in enumerate(children):
            if i != 0:
                if type(child) in (Str, Num):
                    child = child.value
            self.children.append(child)

        super().__init__(children=self.children)

    def __len__(self):
        return len(self.children)

    def __str__(self):
        children = ".".join([str(a) for a in self.children])
        return f"Id({children})"

    __repr__ = __str__
