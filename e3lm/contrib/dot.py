"""
Author: Kenan Masri

`DotPlugin` is an E3lm interpreter plugin used to provide a `dot` attribute
to the main program, containing the text that can be used to generate
a dot graph with `graphviz` package.
"""
import textwrap
from copy import deepcopy
from e3lm.lang import ast
from e3lm.lang.interpreters import E3lmPlugin
from e3lm.lang.data import basic_dt


class DotPlugin(E3lmPlugin):
    """An E3lm interpreter plugin used to provide a `dot` attribute to the main
    program, containing the text that can be used to generate a dot graph with
    `graphviz` package."""
    PROGRAM = {
        "shape": "egg",
        "fillcolor": "orange",
        "color": "black",
        "style": "filled",
        "label": "AST",
    }
    BLOCK = {
        "shape": "egg",
        "fillcolor": "orange",
        "color": "orange",
        "style": "filled",
        "label": "Block",
    }
    AST = {
        "shape": "circle",
        "fillcolor": "pink",
        "color": "black",
        "style": "filled",
        "label": "AST",
    }
    ATTR = {
        "shape": "rect",
        "fillcolor": "pink",
        "color": "black",
        "style": "filled",
        "label": "Attr",
    }
    EXPR = {
        "shape": "rect",
        "fillcolor": "lightblue",
        "color": "blue",
        "style": "filled",
        "label": "<>"
    }
    FUNC = {
        "shape": "circle",
        "fillcolor": "pink",
        "color": "pink",
        "style": "filled",
        "label": "Function",
    }

    def __init__(self, *args, **kwargs):
        self.options = kwargs
        self._ids = 0
        self.dots = {
            "links": []
        }

    def id(self):
        self._ids += 1
        return self._ids - 1

    def interpret(self, input):
        self.program = input
        program_dot = self.visit(input)
        ptv = ParseTreeVisualizer(program_dot, self)
        dot_text = ptv.gendot()
        self.program.dot_text = dot_text
        return self.program

    def visit(self, node):
        result = super().visit(node)
        if type(result) not in basic_dt and result != None:
            if not hasattr(result, "dot"):
                result.dot = {}
            if "id" not in result.dot.keys():
                result.dot["id"] = self.id()
                # result._id if hasattr(result, "_id") else self.id()
        return result

    def dot_Program(self, node):
        dot = deepcopy(self.PROGRAM)
        dot["label"] = "Program"
        dot["children"] = node.blocks
        return dot

    def dot_Block(self, node):
        dot = deepcopy(self.BLOCK)
        ch = [
            *node.children,
            *[b for a, b in node._attrs.items() if a != "body"],
        ]
        if "body" in node._attrs.keys():
            ch.append(node._attrs["body"])

        dot["label"] = str(node.type + ((": "+node.name) if node.name else ""))
        dot["children"] = ch
        return dot

    # def dot_Type(self, node):
    #     dot = deepcopy(self.EXPR)
    #     dot["label"] = node.value
    #     dot["children"] = []
    #     return dot

    def dot_Attr(self, node):
        dot = deepcopy(self.ATTR)
        dot["label"] = node.name
        dot["children"] = [node.value]
        if hasattr(node, "eval"):
            if node.name != "body":
                dot["extra"] = self.link_dot(node)
        if node.name == "body":
            if hasattr(node, "body_tokens"):
                if "rtl" in node.body_tokens:
                    dot["align"] = "rtl"
                elif "ltr" in node.body_tokens:
                    dot["align"] = "ltr"
                elif "center" in node.body_tokens:
                    dot["align"] = "center"
        return dot

    def dot_BinOp(self, node):
        dot = deepcopy(self.EXPR)
        dot["label"] = node.op
        dot["children"] = [node.left, node.right]
        return dot

    def dot_UnaryOp(self, node):
        dot = deepcopy(self.EXPR)
        dot["label"] = node.op
        dot["children"] = [node.value]
        return dot

    def dot_Num(self, node):
        dot = deepcopy(self.EXPR)
        # Use value as is. str because label.
        dot["label"] = str(node.value)
        return dot

    def dot_Str(self, node):
        dot = deepcopy(self.EXPR)
        q = ""
        if node.type == "SINGLEQ1":
            q = "'"
        if node.type == "SINGLEQ2":
            q = "\""
        if node.type == "TRIPLEQ1":
            q = "'''"
        if node.type == "TRIPLEQ2":
            q = "\"\"\""
        dot["label"] = q + str(node.value) + q
        # Replacements for correct output.
        dot["label"] = dot["label"].replace("\\", "\\\\")  # Double escapes
        dot["label"] = dot["label"].replace("\"", "\\\"")  # Double escaped q
        dot["label"] = dot["label"].replace("'", "\\\'")  # Single q
        return dot

    def dot_Bool(self, node):
        dot = deepcopy(self.EXPR)
        dot["label"] = "true" if node.value else "false"
        return dot

    def dot_Undefined(self, node):
        dot = deepcopy(self.EXPR)
        dot["label"] = "none"
        return dot

    def dot_Array(self, node):
        dot = deepcopy(self.EXPR)
        dot["label"] = node.__str__()
        dot["children"] = node.children
        return dot

    def dot_Index(self, node):
        dot = deepcopy(self.EXPR)
        dot["label"] = node.__str__()
        return dot

    def dot_Dict(self, node):
        dot = deepcopy(self.EXPR)
        dot["label"] = node.__str__()
        dot["children"] = node.children
        return dot

    def dot_DictCouple(self, node):
        dot = deepcopy(self.EXPR)
        dot["label"] = str(node.left) + " -> " + str(node.right)
        return dot

    def dot_Func(self, node):
        dot = deepcopy(self.EXPR)
        if node.children:
            chtitle = "." + str(len(node.children)) + "."
            children = node.children
        else:
            chtitle = ""
            children = []

        # Print eval node or its link.
        dot["label"] = f"{node.value}({chtitle})"
        dot["children"] = children
        dot["extra"] = self.link_dot(node) if hasattr(node, "eval") else ""
        return dot

    # def dot_FuncArgs(self, node):
    #     dot = deepcopy(self.EXPR)
    #     dot["children"] = node.children
    #     dot["label"] = self.__str__()
    #     return dot

    def dot_Identifier(self, node):
        dot = deepcopy(self.EXPR)
        dot["label"] = node.__str__()
        dot["children"] = node.children
        dot["extra"] = self.link_dot(node) if hasattr(node, "eval") else ""
        return dot

    def link_dot(self, node):
        _dot = ""
        do_node = True
        if node.eval != None:
            if isinstance(node.eval, ast.AST):
                # if not hasattr(node.eval, "dot"):
                #     if hasattr(node.eval, "target"):
                #         dottu = node.eval.target.dot["id"]
                #         _dot = "node{num} -> node"\
                #             + str(dottu) + "\n"
                #         do_node = False
                #     else:
                #         do_node = True
                # else:
                if node.eval != node:
                    dottu = node.eval.dot["id"]
                    _dot = "node{num} -> node"\
                        + str(dottu) + "\n"
                    do_node = False
                else:
                    do_node = False
        if do_node:
            string = str(node.eval)
            string = string.replace("{", "{{")
            string = string.replace("}", "}}")
            string = string.replace("\\", "\\\\")  # Double escapes
            string = string.replace("\"", "\\\"")  # Double escaped q
            string = string.replace("'", "\\\'")  # Single q
            _dot = "node{num}eval [\
shape=rect,fillcolor=lightyellow,\
color={color},style={style},label=\""+str(string)+"\"]\n\
node{num} -> node{num}eval [color=blue]\n"
        return _dot


class ParseTreeVisualizer(object):
    def __init__(self, parsed, interpreter=None):
        self.parsed = parsed
        self.ncount = 1
        self.dot_header = [textwrap.dedent("""\
        digraph astgraph {
          node [shape=egg, fontsize=13, fontname="Arial", height=.2];
          ranksep=1;
          edge [arrowsize=.5]
        """)]
        self.dot_body = []
        self.dot_footer = ['}']
        self.interpreter = interpreter

    def draw(self, parent, node):
        # --- Node ---
        # Any class of current node.
        if not isinstance(node, basic_dt):
            if not hasattr(node, "dot"):
                node.dot = {}
                node.dot["id"] = self.ncount
                self.ncount += 1

            num = node.dot["id"]
            s, node.dot_children = self.get_dot_data(node, num)

        # Node is not a class. If it belongs to a body Attr, create a Str.
        elif type(parent) == ast.Attr and parent.name == "body":
            str_node = ast.Str(node)
            str_node.dot = {}
            str_node.dot["align"] = "left" if not "rtl" in parent.body_tokens \
                else "right"
            str_node.type = "NO_QUOTE"
            str_node.dot["id"] = self.ncount
            self.ncount += 1
            num = str_node.dot["id"]
            s, str_node.children = self.get_dot_data(str_node, num, {
                "color": "black",
                "fillcolor": "white",
            })
            del str_node

        elif hasattr(parent, "target"):
            s = ""
            if not hasattr(parent.target, "dot"):
                raise Exception("Target " + str(parent.target)
                                + " does not have 'dot'.")

        # Unrecognized.
        else:
            if isinstance(node, basic_dt):
                num = self.ncount
                s = ' node{} [shape={},fillcolor={},\
color={},style={},label="{}"]\n'.format(
                    num, "rect", "lightcyan", "lightblue", "filled", node,
                )
            else:
                num = node._id
                s = ' node{} [shape={},fillcolor={},\
color={},style={},label="{}"]\n'.format(
                    num, "rect", "red", "red", "filled", node,
                )
        self.dot_body.append(s)

        # --- Connecting line ---
        if parent:
            s = ""
            if hasattr(parent, "target"):
                n = parent.target
                if not parent.dot["id"] == n.dot["id"]:
                    col = "red"
                    s = '  node{} -> node{} [color={}]\n'.format(
                        parent.dot["id"], n.dot["id"], col
                    )
            else:
                if not parent.dot["id"] == num:
                    col = "black"
                    s = '  node{} -> node{} [color={}]\n'.format(
                        parent.dot["id"], num, col
                    )
            self.dot_body.append(s)

        self.ncount += 1

    def bfs(self, program):
        self.ncount = program._id + 0
        self.queue = []
        s, program.dot_children = self.get_dot_data(program, program.dot["id"])
        self.dot_body.append(s)
        self.ncount += 1
        self.queue.append(program)
        main_node = program

        while self.queue:
            node = self.queue.pop(0)
            if hasattr(node, "dot_children"):
                for child_node in node.dot_children:
                    if not isinstance(node, basic_dt):
                        self.draw(node, child_node)
                        self.queue.append(child_node)
            else:
                if not isinstance(node, basic_dt):
                    self.draw(main_node, node)
                    self.queue.append(node)

    def gendot(self):
        tree = self.parsed
        self.bfs(tree)
        v = ''.join(self.dot_header + self.dot_body + self.dot_footer)
        return v

    def get_dot_data(self, node_or_dot, num, dots={}):
        if isinstance(node_or_dot, ast.AST):
            dotd = None
            if self.interpreter:
                f = "dot_"+node_or_dot.__class__.__name__
                if hasattr(self.interpreter, f):
                    dotd = getattr(self.interpreter, f)(node_or_dot)
            if dotd == None:
                raise NotImplementedError("Cannot get dot data for nodes \
                    without an interpreter.")
        else:
            dotd = node_or_dot
        children = dotd["children"] if "children" in dotd.keys() else []
        return self.stringify_dot(dotd, num, dots), children

    def stringify_dot(self, dotd, num, dots={}):
        dot = {**dotd, **dots}
        if "align" in dot.keys():
            if dot["align"] in ("left", "ltr", "l"):
                dot["label"] = "\\l".join(dot["label"].splitlines()) + "\\l"
            elif dot["align"] in ("right", "rtl", "r"):
                dot["label"] = "\\r".join(dot["label"].splitlines()) + "\\r"

        q = "\"" if not dot["label"].startswith("<") else ""
        s = ' node{} [shape={},fillcolor={},color={},style={},label={}]\n'
        s = s.format(num,
                     dot["shape"], dot["fillcolor"], dot["color"], dot["style"],
                     q + dot["label"] + q
                     )

        if "extra" in dot.keys():
            s += dot["extra"].format(
                num=num, shape=dot["shape"], fillcolor=dot["fillcolor"],
                color=dot["color"], style=dot["style"], label=dot["label"],
            )
        return s
