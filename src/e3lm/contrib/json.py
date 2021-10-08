"""
Author: Kenan Masri

`JsonPlugin` is an E3lm interpreter plugin used to provide a `json` attribute
to the main program, containing a json string.
The plugin can have options such as `ast` to determine whether to generate
an AST or a tree with evaluated attributes.
"""
import json
from e3lm.helpers.printers import cprint
from e3lm.lang.interpreters import E3lmInterpreter
from e3lm.lang import ast


class JsonPlugin(E3lmInterpreter):
    """An E3lm interpreter plugin used to provide a `json` attribute to the
    main program, containing a json string."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = kwargs

    def interpret(self, input, source=None):
        self.program = input
        program_json = self.visit(self.program)
        self.program.json = program_json
        return self.program

    def v_Program(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        s = {**s,
             "imports": obj.imports,
             }
        s["blocks"] = []
        for i, b in enumerate(obj.blocks):
            s["blocks"].append(self.visit(b))
        return s

    def v_Block(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        s = {**s,
             "name": obj.name,
             "type": obj.type,
             }
        s["attrs"] = {}  # Attrs first in s then children.
        s["children"] = []

        # Visit children first then attributes.
        for i, b in enumerate(obj.children):
            s["children"].append(self.visit(b))

        # Get the ast option. If not specified, detect from post or pre plugin.
        self.from_ast = self.options["ast"] \
            if "ast" in self.options.keys() else None
        if self.from_ast == None:
            self.from_ast = False
            if hasattr(self, "is_plugin") and self.is_plugin == True:
                if self.is_pre:
                    from_ast = True
            elif hasattr(self, "is_pre") and self.is_pre == True:
                from_ast = True
        if self.from_ast:
            # Get the ast attribute values.
            for i, a in obj._attrs.items():
                s["attrs"][i] = self.visit(a)
        else:
            # Get the visited attribute values.
            for i, a in obj.attrs.items():
                s["attrs"][i] = self.visit(a)
        return s

    def vgeneric_start(self, obj, *args, **kwargs):
        s = {
            "_type": obj.__class__.__name__,
        }
        return s

    def vgeneric_value(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        s["value"] = self.visit(obj.value)
        return s

    def vgeneric_children(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        s["children"] = [self.visit(a) for a in obj.children]
        return s

    def vgeneric_string(self, obj, *args, **kwargs):
        s = str(obj)
        return s

    def v_Func(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        s["value"] = obj.value
        s["children"] = []
        if obj.children:
            s["children"] = [self.visit(a) for a in obj.children]
        return s

    def v_Num(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        # Stringify the values not supported by JSON
        s["type"] = obj.type
        s["value"] = obj.eval if s["type"] in ("NUM_INT", "NUM_FLOAT",) \
            else str(obj.value)
        return s

    def v_Str(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        s["type"] = obj.type
        s["value"] = obj.value
        return s

    def v_Undefined(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        s["value"] = "null"
        return s

    # Visiting OPs is implied when ast option is True.
    def v_BinOp(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        s["op"] = obj.op
        s["right"] = self.visit(obj.right)
        s["left"] = self.visit(obj.left)
        return s

    def v_UnaryOp(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        s["op"] = obj.op
        s["value"] = self.visit(obj.value)
        return s

    def v_DictCouple(self, obj, *args, **kwargs):
        s = self.vgeneric_start(obj)
        s["left"] = self.visit(obj.left)
        s["right"] = self.visit(obj.right)
        return s

    def v_Attr(self, obj, *args, **kwargs):
        # Names are the keys of the dict "attrs" of block.
        s = self.vgeneric_start(obj)
        s["value"] = self.visit(obj.value)
        if hasattr(obj, "tokens"):
            s["tokens"] = obj.tokens
        return s

    v_Type = vgeneric_value
    v_Identifier = vgeneric_children
    v_Index = vgeneric_value
    v_Array = vgeneric_children
    v_Dict = vgeneric_children
    v_Bool = vgeneric_value

    def v_dict(self, obj, *args, **kwargs):
        d = {}
        for i, j in obj.items():
            if type(i) not in (str, int,):  # Dict keys must be int or str.
                if type(i) == ast.Identifier:
                    i = i.children[0]
                if type(i) == ast.Num \
                        or type(i) == ast.Str:
                    i = self.visit(i)["value"]
            d[i] = self.visit(j)
        return d

    def v_list(self, obj, *args, **kwargs):
        l = []
        for i, j in enumerate(obj):
            l.append(self.visit(j))
        return l

    def v_bool(self, obj, *args, **kwargs):
        return obj

    v_tuple = vgeneric_string
    v_complex = vgeneric_string
