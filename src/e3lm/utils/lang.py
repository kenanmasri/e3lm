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
    `lexer`, `source`
    and the rest are used for building the lexer
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
        tokmap = []
        for tok in l:
            tokmap.append(tok)
        return tokmap
    else:
        return l


def parse(text,
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
    parser.build(lexer=lexer, **parser_kwargs)

    return parser.parse(text, **kwargs)


def interpret(text,
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
    result = pre_interpreter.interpret(text)
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
        _result = plugin.interpret(result)
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
