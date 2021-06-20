from e3lm.lang.interpreters import (
    E3lmInterpreter,
    get_attr, dot_get,
)
from e3lm.lang import ast
from e3lm.utils.lang import interpret
from e3lm.lang.lexer import E3lmLexer
from e3lm.lang.parser import E3lmParser
from e3lm.demos import data


def test_backflow():
    block1 = ast.Block("Dummy", attrs={
        "attr1": ast.Attr("attr1", 0)
    }, name="block1")

    block2 = ast.Block("Dummy")
    block3 = ast.Block("Dummy")

    blocks = [
        block1,
        block2,
        block3,
    ]

    program = ast.Program(blocks=blocks)
    program.build_flat()
    assert block1 == get_attr(program, "block1")


def test_dotget():
    program = interpret(data.code4)
    assert "hello" == dot_get(program, "my1.attr2.0.1.2.hi")
