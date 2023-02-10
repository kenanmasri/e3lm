import pytest
from e3lm.helpers import printers
from e3lm.demos import data
from e3lm.lang.lexer import E3lmLexer
from e3lm.utils.lang import lex

lexer = E3lmLexer()


def test_lexer():
    for i, d in enumerate(data.examples):
        if "lex" not in d.keys():
            continue

        with_stmt = False
        print(d["raises"], i, d["ind"])
        if "raises" in d.keys():
            with_stmt = "lex" in d["raises"]
            print(with_stmt)

        lexer.build(debug=0)
        er = None
        if with_stmt:
            with pytest.raises((IndentationError, SyntaxError,)) as e:
                lexed = lex(d["text"], lexer=lexer,
                            source=str(i)+":"+str(d["ind"]))
                toks = [t.type for t in lexed]
            er = e.value
        else:
            lexed = lex(d["text"], lexer=lexer,
                        source=str(i)+":"+str(d["ind"]))
            toks = [t.type for t in lexed]

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
                                "Code {} did not raise {} error."
                                .format(str(i), a[1]["class"])
                            )
