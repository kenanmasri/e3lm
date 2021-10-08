import json
import pytest
from e3lm.helpers import printers
from e3lm.demos import data
from e3lm.lang.lexer import E3lmLexer
from e3lm.lang.parser import E3lmParser
from e3lm.contrib.json import JsonPlugin as Json
from e3lm.contrib.dot import DotPlugin as Dot
from e3lm.contrib.units import UnitsPlugin as Units
from e3lm.lang.interpreters import dot_get
from e3lm.utils.lang import interpret

lexer = E3lmLexer()
parser = E3lmParser()


def enum(key, plugins, i, d):
    printers.cprint("test_{}: Code ".format(key) + str(i))
    lexer.build(debug=0)
    parser.build(debug=0, lexer=lexer, tracking=True)
    er = None
    try:
        program = interpret(d["text"], parser=parser, plugins=plugins)
    except (IndentationError,
            SyntaxError, AttributeError, ValueError,
            NotImplementedError, IndexError, TypeError) as e:
        er = e
        program = None
    return program, er


def test_json():
    for i, d in enumerate(data.examples):
        if "json" not in d.keys():
            continue
        json1 = Json()
        json2 = Json(ast=True)
        program, er = enum("json", [json1, json2], i, d)
        if type(d["json"]) == dict:
            _d = d["json"]
            if type(_d) == dict:
                if "assert" in _d.keys():
                    for a in _d["assert"]:
                        if program:
                            json_data = json.dumps(program.json, indent=2)
                            dot = dot_get(json_data, a[0])
                            assert dot == a[1]


def test_dot():
    for i, d in enumerate(data.examples):
        if "dot" not in d.keys():
            continue
        dot = Dot()
        program, er = enum("dot", [dot], i, d)

        if type(d["dot"]) == dict:
            _d = d["dot"]
            if type(_d) == dict:
                if "assert" in _d.keys():
                    for a in _d["assert"]:
                        assert a in program.dot


def test_units():
    for i, d in enumerate(data.examples):
        if "units" not in d.keys():
            continue
        program, er = enum("units", [Units], i, d)
        # print("xx", dot_get(program, "dummy_1.attr1").convert("m"))
        # print("xx", dot_get(program, "dummy_1.attr2").convert("m"))

        if type(d["units"]) == dict:
            _d = d["units"]
            if type(_d) == dict:
                if "assert" in _d.keys():
                    for a in _d["assert"]:
                        if program:
                            assert a[1] == dot_get(program, a[0])
