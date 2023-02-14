"""
Author: Kenan Masri

"""

import json
import types
import inspect as _inspect
from e3lm.helpers.printers import cprint
from e3lm.lang.parser import E3lmParser
from e3lm.lang.lexer import E3lmLexer
from e3lm.lang.interpreters import E3lmInterpreter

_lexer = E3lmLexer()
_parser = E3lmParser()


def lex(text, source=None, lexer=None, token_map=True, **kwargs):
    """Lex text.

    `lexer`, `source` and the rest are used for building the lexer
    """
    srs = source or "<string>"

    if not lexer:
        l = _lexer
    else:
        l = lexer
        if _inspect.isclass(l):
            l = l()

    l.build(**kwargs)
    l.input(text, srs)
    if token_map:
        tokens = l.get_tokens()
        tokmap = []
        for tok in tokens:
            tokmap.append(tok)
        return tokmap
    else:
        return l.token


def parse(text, source=None,
          lexer=None, lexer_kwargs={},
          parser=None, parser_kwargs={},
          **kwargs
          ):  # pragma: no cover

    lexer = lexer \
        or (1 if "lexer" in parser_kwargs.keys() else None)\
        or _lexer
    if lexer == 1:
        lexer = parser_kwargs.pop("lexer")

    parser = parser or _parser
    lexer_kwargs = lexer_kwargs \
        or (parser_kwargs["lexer_kwargs"]
            if "lexer_kwargs" in parser_kwargs.keys() else {})

    parse_kwargs = kwargs \
        or (parser_kwargs["parse_kwargs"]
            if "parse_kwargs" in parser_kwargs.keys() else {})

    lexer.build(**lexer_kwargs)
    parser.build(lexer=lexer, **parse_kwargs)

    return parser.parse(text, source, **kwargs)


def interpret(text, source=None,
              interpreter_cls=E3lmInterpreter,
              parser=None, parser_kwargs={},
              plugins=[],
              **kwargs
              ):  # pragma: no cover

    p = parser or _parser
    if _inspect.isclass(p):
        p = p()
    p.build(**parser_kwargs)

    pre_interpreter = interpreter_cls(parser=p)

    # PRE E3lm
    result = pre_interpreter.interpret(text, source)
    pipe = [pre_interpreter.__class__.__name__]

    if result == None:
        return None

    worked = []
    for plugin in plugins:
        if _inspect.isclass(plugin):
            plugin = plugin()
            plugin.is_plugin = True
            plugin.is_pre = True
            plugin.is_post = False
        _result = plugin.interpret(result, source)
        if _result:
            result = _result
            worked.append(plugin)
            pipe.append(plugin.__class__.__name__)
        elif _result == None:
            raise BrokenPipeError(1, pipe, "Could not continue pipe.")

    for plugin in worked:
        if hasattr(plugin, "post_process"):
            result = plugin.post_process(result)
            if result == None:
                raise ValueError("'{}' post_process did not return Program."
                                 .format(plugin.__class__.__name__))

    return result


def get_plugin(string):
    """Gets an E3lm plugin from the plugins contrib folder or a directory
    specified by the env variable `E3LM_PYTHON_PLUGINS_DIR`.

    Plugins are classes that extend E3lmPlugin and the file name is the
    plugin name. For example "json" plugin is from the file "json.py"
    and the class name is JsonPlugin. The class name is the plugin name
    but the first letter is uppercased plus "Plugin".

    If the custom plugin folder does not have __init__.py, it is ignored and
    fallbacks to E3lmPlugin default directory.
    """
    import os
    res = {}
    dirs = []
    os.environ.setdefault(
        "E3LM_PYTHON_PLUGINS_DIR", "e3lm_plugins")
    pluginsdir = os.environ.get("E3LM_PYTHON_PLUGINS_DIR")
    if not os.path.exists(pluginsdir) or not os.path.isdir(pluginsdir):
        pluginsdir = os.path.abspath(os.path.join(os.path.dirname(
            os.path.realpath(__file__)), '..' + os.sep, 'contrib'))

    if not os.path.isdir(pluginsdir) or not os.path.exists(pluginsdir + os.sep + "__init__.py"):
        pluginsdir = os.path.abspath(os.path.join(os.path.dirname(
            os.path.realpath(__file__)), '..' + os.sep, 'contrib'))

    if not os.path.isdir(pluginsdir) or not os.path.exists(pluginsdir + os.sep + "__init__.py"):
        raise ImportError("E3lm cannot find plugin \"" + str(string) +
                          "\" in the plugins dir \"" + pluginsdir + "\".")

    if not string.endswith(".py"):
        string = string + ".py"
    if os.path.exists(pluginsdir + os.sep + string):
        if not os.path.isfile(pluginsdir + os.sep + string):
            raise ImportError("E3lm cannot import directory as plugin \"" +
                              str(string) + "\" in the plugins dir \"" + pluginsdir + "\".")
        try:
            module = __import__("e3lm.contrib." + string[:-3], fromlist=["*"])
            x = getattr(module, string[0].upper() + string[1:-3] + "Plugin")
            return x
        except ImportError as e:
            raise e
        except AttributeError as e:
            raise e
    raise ModuleNotFoundError("Could not find e3lm plugin \"" + str(string[:-3]) + "\".")