import pytest
from e3lm.helpers import printers
from e3lm.demos import data
from e3lm.lang.parser import E3lmParser
from e3lm.utils.lang import parse

parser = E3lmParser()


def test_parser_errors():
    for i, d in enumerate(data.examples):
        if "parse" not in d.keys():
            continue
        printers.cprint("test_parser: Code "+str(i))
        parser.build(debug=1)
        er = None
        try:
            parsed = parse(d["text"], parser=parser, debug=0, tracking=True)
        except (IndentationError, SyntaxError) as e:
            er = e

        if type(d["parse"]) == dict:
            _d = d["parse"]
            if "assert" in _d.keys():
                passerts = 0
                passerts_count = len([pe for pe in _d['assert']
                                      if pe[0] == "p_error"])
                for a in _d["assert"]:
                    if a[0] == "error":
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
                    elif a[0] == "p_error":
                        for i, er in enumerate(parser.errors):
                            asserted = False
                            if "class" in a[1].keys():
                                if er[0][0].__name__ == a[1]["class"]:
                                    if "lineno" in a[1].keys():
                                        if er[0][2] == a[1]["lineno"]:
                                            asserted = True

                            if asserted:
                                passerts += 1
                            # else:
                            #     print(er[0][0].__name__, er[0][2])

                assert passerts == passerts_count
