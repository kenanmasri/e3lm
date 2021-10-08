"""
Author: Kenan Masri

`DotPlugin` is an E3lm interpreter plugin used to provide a `dot` attribute
to the main program, containing the text that can be used to generate
a dot graph with `graphviz` package.
"""
import textwrap
from graphviz import Graph
from copy import deepcopy
from e3lm.lang import ast
from e3lm.lang.interpreters import E3lmPlugin
from e3lm.lang.data import basic_dt


class ParseTreeVisualizer(object):
    def __init__(self, parsed, interpreter=None, rankdir="LR"):
        self.parsed = parsed
        self.ncount = 1
        self.dot_header = [textwrap.dedent("""digraph G {\
  graph [bgcolor="#22222222", rankdir=""" + rankdir + """]
  node [fontcolor="white" fontname="Arial" fontsize=13 height=.3 rankdir=LR ranksep=1 shape=rect]
  edge [arrowsize=.6 color="#666666"]
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
            str_node.dot["align"] = "left" if not "rtl" in parent.tokens \
                else "right"
            str_node.type = "NO_QUOTE"
            str_node.dot["id"] = self.ncount
            self.ncount += 1
            num = str_node.dot["id"]
            s, str_node.children = self.get_dot_data(str_node, num, {
                "color": "white",
                "fillcolor": "#f087c5a0:#edab59a0",
                "gradientangle": 135,
            })
            del str_node

        elif hasattr(parent, "target"):
            s = ""
            if not hasattr(parent.target, "dot"):
                raise Exception("Target " + str(parent.target)
                                + " does not have 'dot'.")

        # Unrecognized nodes.
        else:
            if isinstance(node, basic_dt):
                num = self.ncount
                s = ' node{} [shape={},fillcolor={},color={},style={},label="{}"]\n'.format(
                    num, "rect", "\"#53004350\"", "\"#d300d3\"", "filled", node,
                )
            else:
                num = node._id
                s = ' node{} [shape={},fillcolor={},color={},style={},label="{}"]\n'.format(
                    num, "rect", "red", "red", "filled", node,
                )
        self.dot_body.append(s)

        # --- Connecting line ---
        if parent:
            s = ""
            if hasattr(parent, "target"):
                n = parent.target
                if not parent.dot["id"] == n.dot["id"]:
                    col = "#000077"
                    s = '  node{} -> node{} [color="{}"]\n'.format(
                        parent.dot["id"], n.dot["id"], col
                    )
            else:
                if not parent.dot["id"] == num:
                    col = "#303077"
                    s = '  node{} -> node{} [color="{}"]\n'.format(
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
        s = ' node{} [shape="{}",fillcolor="{}",color="{}",style="{}",label={}]\n'
        s = s.format(num,
                     dot["shape"], dot["fillcolor"], dot["color"], dot["style"],
                     q + dot["label"] + q
                     )

        if "extra" in dot.keys():
            s += dot["extra"].format(
                num=num, shape=dot["shape"], fillcolor=dot["fillcolor"],
                color=dot["color"], style=dot["style"], label=dot["label"],
                fontcolor=dot["fontcolor"],
            )
        return s


class DotPlugin(E3lmPlugin):
    """An E3lm interpreter plugin used to provide a `dot` attribute to the main
    program, containing the text that can be used to generate a dot graph with
    `graphviz` package."""

    RANKDIR = "LR"
    SIZE = '6,9'

    NODES = {
        "Program": {
            "shape": "diamond",
            "fillcolor": "#000000A0",
            "fontcolor": "#d300d3",
            "color": "#d38400",
            "style": "filled",
            "label": "Program",
        },
        "Block": {
            "shape": "square",
            "fillcolor": "#d3840050",
            "fontcolor": "#7e0e7e",
            "color": "#d38400",
            "style": "filled",
            "label": "Block",
        },
        "AST": {
            "shape": "circle",
            "fillcolor": "pink",
            "color": "white",
            "style": "filled",
            "label": "AST",
        },
        "Attr": {
            "shape": "rect",
            "fillcolor": "#d3840050",
            "fontcolor": "#d384a0",
            "color": "#d38400",
            "style": "filled",
            "label": "Attr",
        },
        "Expr": {
            "shape": "rect",
            "fillcolor": "#7e0e7e50",
            "color": "#7e0e7e",
            "fontcolor": "white",
            "style": "filled",
            "label": "<>"
        },
        "Func": {
            "shape": "circle",
            "fillcolor": "pink",
            "color": "pink",
            "style": "filled",
            "label": "Function",
        },
        "eval": {
            "shape": "rectangle",
            "color": "#167cd6",
            "fontcolor": "#167cd6",
            "fillcolor": "#000000",
        },
    }

    def __init__(self, **kwargs):
        self.options = kwargs
        self._ids = 0
        self.g = g = Graph('G')
        self.g.attr('graph', bgcolor="#22222222")
        self.g.attr('node', fontname="Arial", fontcolor="white", shape="rect",
                    fontsize="13", height=".3", ranksep="1", rankdir=self.RANKDIR)
        self.g.attr('edge', color="#666666", arrowsize=".6")

    def id(self):
        self._ids += 1
        return int(self._ids - 1)

    def interpret(self, program, source=None):
        self.program = program
        self.program = self.visit(self.program)
        self.ptv = ParseTreeVisualizer(
            self.program, self, rankdir=self.RANKDIR)
        self.program.dot_source = self.ptv.gendot()
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
        dot = deepcopy(self.NODES["Program"])
        dot["label"] = "Program"
        dot["children"] = node.blocks
        return dot

    def dot_Block(self, node):
        dot = deepcopy(self.NODES["Block"])
        ch = [
            *node.children,
            *[b for a, b in node._attrs.items() if a != "body"],
        ]
        if "body" in node._attrs.keys():
            ch.append(node._attrs["body"])
        dot["label"] = str(node.type + ((": "+node.name) if node.name else ""))
        dot["children"] = ch
        return dot

    def dot_Attr(self, node):
        dot = deepcopy(self.NODES["Attr"])
        dot["label"] = node.name
        dot["children"] = [node.value]
        if hasattr(node, "eval"):
            if node.name != "body":
                pass
                dot["extra"] = self.link_dot_eval(
                    node) if hasattr(node, "eval") else ""
        if node.name == "body":
            if hasattr(node, "tokens"):
                if "rtl" in node.tokens:
                    dot["align"] = "rtl"
                elif "ltr" in node.tokens:
                    dot["align"] = "ltr"
                elif "center" in node.tokens:
                    dot["align"] = "center"
        return dot

    def dot_BinOp(self, node):
        dot = deepcopy(self.NODES["Expr"])
        dot["label"] = node.op
        dot["children"] = [node.left, node.right]
        return dot

    def dot_UnaryOp(self, node):
        dot = deepcopy(self.NODES["Expr"])
        dot["label"] = node.op
        dot["children"] = [node.value]
        return dot

    def dot_Num(self, node):
        dot = deepcopy(self.NODES["Expr"])
        # Use value as is. str because label.
        dot["label"] = str(node.value)
        return dot

    def dot_Str(self, node):
        dot = deepcopy(self.NODES["Expr"])
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
        dot = deepcopy(self.NODES["Expr"])
        dot["label"] = "true" if node.value else "false"
        return dot

    def dot_Undefined(self, node):
        dot = deepcopy(self.NODES["Expr"])
        dot["label"] = "none"
        return dot

    def dot_Array(self, node):
        dot = deepcopy(self.NODES["Expr"])
        dot["label"] = node.__str__()
        dot["children"] = node.children
        return dot

    def dot_Index(self, node):
        dot = deepcopy(self.NODES["Expr"])
        dot["label"] = node.__str__()
        return dot

    def dot_Dict(self, node):
        dot = deepcopy(self.NODES["Expr"])
        dot["label"] = node.__str__()
        dot["children"] = node.children
        return dot

    def dot_DictCouple(self, node):
        dot = deepcopy(self.NODES["Expr"])
        dot["label"] = str(node.left) + " -> " + str(node.right)
        return dot

    def dot_Func(self, node):
        dot = deepcopy(self.NODES["Expr"])
        if node.children:
            chtitle = "." + str(len(node.children)) + "."
            children = node.children
        else:
            chtitle = ""
            children = []

        # Print eval node or its link.
        dot["label"] = f"{node.value}({chtitle})"
        dot["children"] = children
        dot["extra"] = self.link_dot_eval(
            node) if hasattr(node, "eval") else ""
        return dot

    def dot_Identifier(self, node):
        dot = deepcopy(self.NODES["Expr"])
        dot["label"] = node.__str__()
        dot["children"] = node.children
        dot["extra"] = self.link_dot_eval(
            node) if hasattr(node, "eval") else ""
        return dot

    def link_dot_eval(self, node):
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
            _dot = "  node{num}eval [\
shape=\"{shape}\",fillcolor=\"indigo\",\
color=\"#119ec1\",style=\"{style}\",label=\""+str(string)+"\"]\n\
  node{num} -> node{num}eval [color=\"blue\"]\n"
        return _dot
