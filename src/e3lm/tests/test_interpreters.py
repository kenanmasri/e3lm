import pytest
from e3lm.helpers import printers
from e3lm.lang import ast
from e3lm.demos import data
from e3lm.lang.lexer import E3lmLexer
from e3lm.lang.parser import E3lmParser
from e3lm.utils.lang import interpret
from e3lm.lang.interpreters import dot_get

lexer = E3lmLexer()
parser = E3lmParser()


def test_basic_interpret():
    for i, d in enumerate(data.examples):
        if "interpret" not in d.keys():
            continue
        printers.cprint("test_interpreters: Code "+str(i))
        lexer.build(debug=0)
        parser.build(debug=0, lexer=lexer, tracking=True)
        er = None
        try:
            program = interpret(d["text"], parser=parser)
        except (IndentationError,
                SyntaxError, AttributeError, ValueError,
                NotImplementedError, IndexError, TypeError) as e:
            er = e

        if type(d["interpret"]) == dict:
            _d = d["interpret"]
            if "assert" in _d.keys():
                for a in _d["assert"]:
                    if a[0] == "error":
                        if er != None:
                            if "class" in a[1].keys():
                                assert er.__class__.__name__ == a[1]["class"]
                            if "lineno" in a[1].keys():
                                assert er.lineno == a[1]["lineno"]
                        else:
                            raise AssertionError(
                                "Code did not raise {} error."
                                .format(a[1]["class"])
                            )
                    else:
                        if er == None:
                            dot = dot_get(program, a[0], eval=True)
                            assert dot == a[1]
                        else:
                            raise AssertionError("No program.")
