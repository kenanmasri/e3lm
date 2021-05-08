import pytest
from e3lm.helpers import printers
from e3lm.tests import data
from e3lm.lang.lexer import E3lmLexer
from e3lm.utils.lang import lex

lexer = E3lmLexer()


def test_lexer():
    for i, d in enumerate(data.examples):
        if "lex" not in d.keys():
            continue
        printers.cprint("test_lexer: Code "+str(i))
        lexer.build(debug=0)
        er = None
        try:
            lexed = lex(d["text"], lexer=lexer)
            toks = [t.type for t in lexed]
        except (IndentationError, SyntaxError) as e:
            er = e

        if type(d["lex"]) == dict:
            _d = d["lex"]
            if "assert" in _d.keys():
                for a in _d["assert"]:
                    if a[0] == "tokens":
                        assert toks == a[1]
                    elif a[0] == "error":
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
