import json
import sys
from e3lm.helpers import printers
from e3lm.utils.lang import lex, parse, interpret
from e3lm.contrib.json import JsonPlugin as Json
from e3lm.contrib.dot import DotPlugin as Dot
from e3lm.contrib.units import UnitsPlugin as Units
from e3lm.lang.parser import E3lmParser
from e3lm.tests import data as testdata

if __name__ == "__main__":
    args = sys.argv

    codes = {}

    do_lex = False
    do_parse = False
    do_interpret = False
    do_json = False
    do_units = False
    do_ast = False
    do_view = False
    debug = 1
    plugins = []

    for arg in args:
        if arg == "help":
            print("Usage: e3lm [lex|parse|interpret] [json|units|ast] [view] \
code[n] [....]\n")
            exit()
        if arg.startswith("code"):
            if arg == "code":
                with open("app.3lm") as f:
                    codes[arg] = {"text": "".join(f.readlines())}
            else:
                if hasattr(testdata, arg):
                    codes[arg] = {"text": getattr(testdata, arg)}
            codes[arg]["options"] = []
            codes[arg]["options"].extend([
                "lex" if do_lex else "",
                "parse" if do_parse else "",
                "interpret" if do_interpret else "",
                "json" if do_json else "",
                "units" if do_units else "",
                "ast" if do_ast else "",
                "view" if do_view else "",
            ])
            codes[arg]["interpret"] = {
                "plugins": plugins,
            }
            codes[arg]["debug"] = debug
            do_lex = False
            do_parse = False
            do_interpret = False
            do_json = False
            do_units = False
            do_ast = False
            do_view = False
            debug = 1
            plugins = []

        if arg == "lex":
            do_lex = True
        if arg == "parse":
            do_parse = True
        if arg == "interpret" or arg == "intr":
            do_interpret = True
        if arg.endswith("dot") or arg.endswith("view"):
            do_view = True
            plugins.append(Dot)
        if arg.endswith("json"):
            do_json = True
            plugins.append(Json)
        if arg.endswith("units"):
            do_units = True
            plugins.append(Units)
        if arg == "ast":
            do_ast = True
        if arg.startswith("debug"):
            try:
                debug = int(arg.split("=")[1])
            except ValueError:
                debug = 1

    if len(codes) == 0:
        do_view_only = do_view
    else:
        do_view_only = False

    for codename, code in codes.items():
        printers.cprint("--- " + codename + " ---", col="SUCCESS")
        do_lex = "lex" in code["options"]
        do_parse = "parse" in code["options"]
        do_interpret = "interpret" in code["options"]
        do_json = "json" in code["options"]
        do_units = "units" in code["options"]
        do_ast = "ast" in code["options"]
        do_view = "view" in code["options"]
        debug = code["debug"]
        if do_lex:
            lex(code["text"], "app.3lm", debug=debug)

        if do_parse:
            parsed = parse(code["text"], parser_kwargs={
                "tracking": True,
                "enable_colors": True,
                "debug": debug,
            }, debug=debug
            )
            if parsed:
                printers.pprint.pp(parsed.blocks)

        if do_interpret:
            plugins = [p(ast=do_ast) for p in code["interpret"]["plugins"]]
            program = interpret(code["text"],
                                plugins=plugins,
                                debug=debug, enable_colors=True,
                                parser_kwargs={
                                    "tracking": True,
                                }
            )
            if program == None:
                print("None")
            if do_json:
                print(json.dumps(program.json, indent=4))
            if do_view:
                if program:
                    from graphviz import Source
                    content = program.dot_text
                    s = Source(content, filename="e3lm.dot", format="png")
                    s.view()
                else:
                    print("No program to dotview")

    else:
        if do_view_only:
            from graphviz import Source
            with open("e3lm.dot") as f:
                content = "".join(f.readlines())
            s = Source(content, format="png")
            s.view()
