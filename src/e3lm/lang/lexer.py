"""
Author: Kenan Masri

E3LM (3lm) language lexing tools.
This module provides an `E3lmLexer` with various other internal classes and\
 methods such as `LexStack` and `raise_lex_error`.

The LexStack is an indent following, state-like stack for the lexer.
The E3lmLexer is our e3lm language lexer.
"""

import re
import tokenize
from ply import lex as plylex
from e3lm.helpers import printers
from e3lm.lang.data import tokens, regexes


def raise_lex_error(t, message, type=IndentationError, file=None, details={}):
    """Raise `type` error on token `t` with `message`. Optionally `file` and
    `details` are provided.

    Args:
        `t`: Token.
        `message`: Display string.
        `type`: Raised error.
        `file`: File name or None (defaults to None which is token lexer \
            source).
        `details`: A dict with optional `lineno` and `lineno_inc`.

    Raises:
        `type`
    """
    if file is None:
        file = t.lexer.source
    # print = t.lexer.e3lm_lexer.print
    # print(t, "ERROR")
    lineno = t.lineno # - 1
    if 'lineno' in details.keys():
        lineno = details['lineno']
    if 'lineno_inc' in details.keys():
        lineno_inc = details['lineno_inc']
        lineno += lineno_inc
    start = t.lexer.line_offsets[lineno]
    if t.type != "eof":
        end = t.lexer.line_offsets[lineno+1]-1
    else:
        end = start
    offset = t.lexpos - start + 1

    # print(message, 'ERROR')
    if type == IndentationError:
        details = {}
    raise type(message, (file, lineno, offset, t.lexer.lexdata[start:end]),
               **details
               )


def convert_string(start_tok, string_toks):
    """Convert list of tokens ``string_toks`` to a string.

    Args:
        `start_tok`: The first letter before string quotes.
        `string_toks`: Tokens.

    Returns:
        `str`: The formed string.

    Raises:
        `AssertionError`
    """
    #  "u"   - convert from unicode
    #  ""    - string

    # First we remove continue-newline tokens and lstrip the token next to it.
    for i, tok in enumerate(string_toks):
        if tok.type == "STRING_CONTINUE_NEWLINE":
            if i+1 < len(string_toks):
                string_toks[i+1].value = string_toks[i+1].value.lstrip(" \t")
            del string_toks[i]

    s = "".join(tok.value for tok in string_toks)
    quote_type = start_tok.value.lower()
    if quote_type == "":
        return s
    elif quote_type == "u":
        return s.encode("utf-8")
    else:
        raise AssertionError(
            "Unknown string quote type: \"%r\"." % (quote_type,))


def bodify_indents(string, indents):
    """Organize indents for body."""
    if string:
        string = string.split("\n")
        new_strings = []
        for s in string:
            i = 0
            for i, ch in enumerate(s[0:indents+1]):
                if ch not in (" ", "\t"):
                    break
            new_strings.append(s[i:])

        return "\n".join(new_strings)
    return string


class LexStack():
    """Simple stack class for use with E3lmLexer.

    Attributes:
        `store`: Data dict.
        `lexer`: The lexer.
        `follow_indentation`: Whether to follow indentations.
        `id`: Current
    """
    store = None
    lexer = None
    follow_indentation = True
    id = 0

    def __init__(self, lexer=None, store=[], **kwargs):
        """Initiate the LexStack.

        Args:
            `lexer`: Lexer to use.
            `store`: Initial data.
            `kwargs`:
                - `follow_indentation`: Follow the indentation
                    after each stack push.
        """
        self.store = store
        self.lexer = lexer
        if "follow_indentation" in kwargs.keys():
            self.follow_indentation = kwargs['follow_indentation']

    def push(self, t, stack, *args, **kwargs):
        """Push stack and if following indents then prepare for the indent \
        setting.

        Args:
            `t`: Token
            `stack`: Dict to append to the store.
            `args`:
                - Push lexer state with a name.

        Returns:
            `int`: New stack ID.
        """
        if type(stack) is not dict:
            raise Exception("Pushed stacks must be a \
            dict.")

        stack["t"] = t

        # New stack will have an _indent_gt. This is the len of the computed
        # indents of the token line.
        # This number will be compared to be GREATER THAN "current" tokens...
        if self.follow_indentation:
            stack["_indent_gt"] = self.lexer.computed["indent"][t.lineno]

        self.store.append(stack)
        self.id = len(self.store) - 1

        if len(args) == 1:
            if args[0]:
                self.lexer.push_state(args[0])

        return self.id

    def pop(self, poplex=False):
        """Pop stack.

        Args:
            `poplex`: Whether to pop lexer's state.

        Returns:
            `dict`: The popped stack.
        """
        if poplex == True:
            self.lexer.pop_state()

        if self.id > 0:
            stack = self.store.pop()
            self.id -= 1
        else:
            stack = None

        return stack

    def follow_indent(self, t, val=None):
        """Check the indents of the given token previous line. That should be
        equal to the token's line indents. In other words, this method is used
        to check that indents are the same.

        Args:
            `t`: Token.
            `val`: Update indents to this value.

        Raises:
            `IndentationError`: If recorded indents do not match
                that of the token's.
        """
        lineno = t.lineno
        indents = self.lexer.computed["indent"][lineno-1]

        if hasattr(self, '_indent_gt'):
            req_indents = self._indent_gt
            self.update('_indent', req_indents)
            indents = self._indent
            del self.store[self.id]["_indent_gt"]
        else:
            req_indents = indents
            indents = self._indent

        if val:
            self.update('_indent', val)

        if req_indents != indents:
            raise_lex_error(
                t,
                "Expected %d indents, got %d." % (req_indents, indents),
                type=IndentationError,
                details={"req_indents": req_indents, "indents": indents, },
            )

    def update(self, key, value, id=None):
        """Update stack data.

        Args:
            `key`: The key of the store dict to update.
            `value`: The value to update to, can be "++" or "--" to init zero \
            or inc/dec.
            `id`: The ID of the store to update, or None to use current \
            (default).
        """
        if id == None:
            id = self.id
        if len(self.store) == 0:
            self.store = [{}]

        if key not in self.store[id].keys():
            if value == "++" or value == "--":
                self.store[id][key] = 0

        if value == "++":
            value = self.store[id][key] + 1
        elif value == "--":
            value = self.store[id][key] - 1

        self.store[id][key] = value

    def __getattr__(self, key):
        id = self.id
        return self.store[id][key] \
            if key in self.store[id].keys() else super().__getattribute__(key)

    def __len__(self):
        return len(self.store)

    def get(self, key, *args, id=None):
        """Get store's value by key.

        Args:
            `id`: The ID of the store to update, or None to use current \
            (default).
            `args`:
                - Default value.

        Returns:
            Value.
        """
        if id is None:
            id = self.id
        default = self.__getattr__(key)
        if len(args) == 1:
            if args[0]:
                default = args[0]

        return self.store[id][key] \
            if key in self.store[id].keys() else default


class E3lmLexer():
    """Lexer for e3lm.

    Attributes:
        `compute_pattern`: This is used to capture meaningful tokens from the \
        source.
        `compute_pattern_inds`: A dict that defines `compute_pattern` indices.
        `_newline_pattern`: Newline regex pattern.
        `debug`: Whether debug mode.
        `print`: Print method used to print debug output.
        `states`: Lexer states.
        `reserved`: Reserved keywords.
        `tokens`: Lexer tokens.
        `checks_tokens`: The tokens to check if followed by one another.
    """
    # --- Class variables ---
    # Pattern to compute indents, actual text and comments.
    # - Indents followed by anything* and semicolon then anything*, and a
    # newline.
    # - Newlines whether preceded by indents or not (nothing afterwards).
    # - Indents followed by anything+ (inc. spaces and tabs), and a newline.
    compute_pattern = re.compile(
        r"(([ \t]*)(.*)(;.*)\n?)|(([ \t]*)\n)|(([ \t]*)(.+)\n?)"
    )
    compute_pattern_inds = {
        # gName: (1st, 2nd, ...),
        "indent": (2, 6, 8,),
        "text": (3, 9,),
        "comment": (4,),
        "newline": (5,),
    }
    _newline_pattern = re.compile(r"\n")
    debug = 0

    def print(self, text, *args):
        return printers._print(
            self.COLORS["LOG"] + "LOG "
            + self.COLORS["LOG_MSG"]
            + text + self.COLORS["RESET"]
        , *args)

    # --- States ---
    states = (
        ("BLOCK", "inclusive"),
        ("BODY",  "inclusive"),
        ("EXPR",  "inclusive"),  # Expression tokens
        ("SINGLEQ1",  "inclusive"),  # string expression '
        ("SINGLEQ2",  "inclusive"),  # string expression "
        ("TRIPLEQ1",  "inclusive"),  # string expression '''
        ("TRIPLEQ2",  "inclusive"),  # string expression """
    )

    # --- Reserved keywords ---
    reserved = {
        'end': 'END',
        'true': 'BOOL',
        'false': 'BOOL',
        'none': 'NONE',
    }

    # --- Token Names ---
    tokens = tokens

    # --- Char Regexes ---
    digit_char = r'[0-9]'
    nondigit_char = r'[_\-A-Za-z]'
    uppercased_char = r'[A-Z]'
    begin_char_up = r'[_A-Z]'
    begin_char = r'[_A-Za-z]'
    cont_char = r'[_A-Za-z0-9]'
    any_char = r'.'
    identifier_char = begin_char + cont_char
    class_name_char = begin_char_up + cont_char

    # Capture Regexes for Tokens
    ## re_digit           = r'(' + digit_char + r')'
    ## re_nondigit        = r'(' + nondigit_char + r')'
    ## re_uppercased      = r'(' + uppercased_char + r')'
    re_identifier = r'(' + identifier_char + r'*)'
    re_class_def = r'(' + class_name_char + r"*)([ \t]*(" + \
         identifier_char + r"*))?"

    # r'[-+]?[0-9]+(\.([0-9]+)?([eE][-+]?[0-9]+)?|[eE][-+]?[0-9]+)'
    re_float = tokenize.Floatnumber

    # --- Variable-based Token Regexes ---
    # Expr
    t_EXPR_PLUS = r'\+'
    t_EXPR_MINUS = r'-'
    t_EXPR_TIMES = r'\*'
    t_EXPR_DIVIDE = r'/'
    t_EXPR_AND = r'\&'
    t_EXPR_OR = r'\|'
    t_EXPR_NOT = r'\!'
    t_EXPR_COLON = r'\:'
    t_EXPR_DOT = r'\.'
    t_EXPR_COMMA = r'\,'

    # Tokens to be checked if other tokens are next to them.
    checks_tokens = (
        {
            "tokens": ("_LITERAL", "_LITERAL"),
            "message": "Literals cannot be followed by other literals.",
        },
        {
            "tokens": ("ID", "ID"),
            "message": "IDs cannot be followed by other IDs.",
        },
        {
            "tokens": ("ID", "ID"),
            "message": "IDs cannot be followed by other IDs.",
        },
        {
            "tokens": ("ID", "_LITERAL"),
            "message": "IDs cannot be followed by a literal.",
        },
        {
            "tokens": ("_LITERAL", "ID"),
            "message": "Literals cannot be followed by an ID.",
        },
    )

    # Ignores
    t_ignore_COMMENT = r'[ \t]*\;(.*)'
    t_ignore_IMPORT = regexes["IMPORT"]

    # -- States --
    # Ignores
    t_BLOCK_ignore_COMMENT = t_ignore_COMMENT
    t_EXPR_ignore_COMMENT = t_ignore_COMMENT
    # supress PLY warning
    t_TRIPLEQ1_ignore = ""
    t_TRIPLEQ2_ignore = ""
    t_SINGLEQ1_ignore = ""
    t_SINGLEQ2_ignore = ""

    # --- Functions ---
    # -- Function-based Token Regexes
    def t_NEWLINE(self, t):
        r"\n"
        return t

    @plylex.TOKEN(re_class_def)
    def t_CLASS(self, t):
        match = t.lexer.lexmatch
        t.value = match.group(3) # 3 is always first in plylex
        if t.value.lower() == "import":
            pass
        else:
            name = match.group(5) if match.group(5) else ""
            if name:
                t.value = (t.value, name)
            # self.stack.push(t, {}, "BLOCK")
            t.lexer.push_state('BLOCK')
            return t

    # Unnecessary tokenization
    # @plylex.TOKEN(re_identifier)
    # def t_ID(self, t):
    #     t.type = self.reserved.get(t.value.lower(), 'ID')
    #     return t

    # - BLOCK state

    def t_BLOCK_END(self, t):
        r'[eE][nN][dD](.*)'
        t.type = "END"
        t.check_indents = True
        self.stack.pop(True)
        self.stack.indent_check = "lt"
        return t

    @plylex.TOKEN(re_identifier + r'\s*\=\s*')
    def t_BLOCK_ATTR(self, t):
        # Remove the equals part by getting the captured value only.
        match = t.lexer.lexmatch
        t.value = match.group(4)  # 4 is the name
        t.type = self.reserved.get(t.value.lower(), 'ATTR')
        if t.type != 'ATTR':
            raise_lex_error(t, "Encountered reserved keyword",
                            type=SyntaxError,
                            )
        t.lexer.push_state('EXPR')
        t.lexer.paren_level = 0
        t.lexer.dict_level = 0
        t.lexer.array_level = 0
        self.stack.update('_indent', self.lexer.computed["indent"][t.lineno])
        # print(self.stack.store)
        return t

    def t_BLOCK_BODYOPEN(self, t):
        r'\-\-\-'
        if t.lexer.last_token.type == "BODY":
            # t.lexer.skip(1)
            # t.lexer.lineno += 1
            return

        t.lexer.body_start = -1
        t.lexer.body_start_lineno = -1
        t.lexer.body_indent = t.lexer.computed['indent'][t.lineno+1]
        self.stack.push(t, {}, "BODY")  # Both

    def t_BLOCK_WS(self, t):
        r'[ \t]'
        return t

    @plylex.TOKEN(re_class_def)
    def t_BLOCK_CLASS(self, t):
        match = t.lexer.lexmatch
        t.value = match.group(8)
        name = match.group(10)
        if name:
            t.value = (t.value, name)
        self.stack.push(t, {}, 'BLOCK')
        # t.lexer.push_state('BLOCK')
        return t

    # @plylex.TOKEN(re_identifier)
    # def t_BLOCK_NAME(self, t):
    #     self.stack.indent_check = "gt"
    #     return t

    def t_BLOCK_NEWLINE(self, t):
        r"\n"
        if t.lexer.last_token:
            if t.lexer.last_token.type == "CLASS":
                self.stack.push(t.lexer.last_token, {})
                self.stack.indent_check = "gt"
        #    elif t.lexer.last_token.type == "NAME":
        #        pass
        return t

    # - EXPR state

    # - escape LINE:
    def t_EXPR_escape(self, t):
        r"\\\n"
        t.lexer.lineno += 1

    # - STRINGS

    # Handle "\[n\]" escapes
    def t_SINGLEQ1_SINGLEQ2_TRIPLEQ1_TRIPLEQ2_escapes(self, t):
        r"\\(.|\n)"
        # If ending line with a \
        if t.value == "\\\n":
            t.type = "STRING_CONTINUE_NEWLINE"
        else:
            t.type = "STRING_CONTINUE"
        t.lexer.lineno += t.value.count("\n")
        return t

    def t_EXPR_start_string_triple_q1(self, t):
        r"[bB]?'''"
        t.lexer.push_state("TRIPLEQ1")
        t.type = "STRING_START_TRIPLEQ1"
        if "r" in t.value or "R" in t.value:
            t.lexer.string_raw = True
        t.value = t.value.split("'", 1)[0]
        return t

    def t_TRIPLEQ1_simple(self, t):
        r"[^']+"
        t.type = "STRING_CONTINUE"
        t.lexer.lineno += t.value.count("\n")
        return t

    def t_TRIPLEQ1_q1_but_not_triple(self, t):
        r"'(?!'')"
        t.type = "STRING_CONTINUE"
        return t

    def t_TRIPLEQ1_end(self, t):
        r"'''"
        t.type = "STRING_END"
        t.lexer.pop_state()
        t.lexer.string_raw = False
        return t

    def t_EXPR_start_string_triple_q2(self, t):
        r'[bB]?"""'
        t.lexer.push_state("TRIPLEQ2")
        t.type = "STRING_START_TRIPLEQ2"
        if "r" in t.value or "R" in t.value:
            t.lexer.string_raw = True
        t.value = t.value.split('"', 1)[0]
        return t

    def t_TRIPLEQ2_simple(self, t):
        r'[^"]+'
        t.type = "STRING_CONTINUE"
        t.lexer.lineno += t.value.count("\n")
        return t

    def t_TRIPLEQ2_q2_but_not_triple(self, t):
        r'"(?!"")'
        t.type = "STRING_CONTINUE"
        return t

    def t_TRIPLEQ2_end(self, t):
        r'"""'
        t.type = "STRING_END"
        t.lexer.pop_state()
        t.lexer.string_raw = False
        return t

    def t_EXPR_string_start_single_q1(self, t):
        r"[bB]?'"
        t.lexer.push_state("SINGLEQ1")
        t.type = "STRING_START_SINGLEQ1"
        if "r" in t.value or "R" in t.value:
            t.lexer.string_raw = True
        t.value = t.value.split("'", 1)[0]
        return t

    def t_SINGLEQ1_simple(self, t):
        r"[^'\\\n]+"
        t.type = "STRING_CONTINUE"
        return t

    def t_SINGLEQ1_end(self, t):
        r"'"
        t.type = "STRING_END"
        t.lexer.pop_state()
        t.lexer.string_raw = False
        return t

    def t_EXPR_string_start_single_q2(self, t):
        r'[bB]?"'
        t.lexer.push_state("SINGLEQ2")
        t.type = "STRING_START_SINGLEQ2"
        if "r" in t.value or "R" in t.value:
            t.lexer.string_raw = True
        t.value = t.value.split('"', 1)[0]
        return t

    def t_SINGLEQ2_simple(self, t):
        r'[^"\\\n]+'
        t.type = "STRING_CONTINUE"
        return t

    def t_SINGLEQ2_end(self, t):
        r'"'
        t.type = "STRING_END"
        t.lexer.pop_state()
        t.lexer.string_raw = False
        return t

    @plylex.TOKEN(tokenize.Imagnumber)
    def t_EXPR_IMAGNUMBER(self, t):
        t.type = "NUM_IMAG"
        t.value = (float(t.value[:-1]) * 1j, t.value)
        return t

    @plylex.TOKEN(re_float)
    def t_EXPR_FLOAT(self, t):
        t.type = "NUM_FLOAT"
        t.value = float(t.value)
        return t

    def t_EXPR_HEXNUMBER(self, t):
        r"0[xX][0-9a-fA-F]+?"
        t.type = "NUM_HEX"
        return t

    def t_EXPR_OCTNUMBER(self, t):
        r"0o[0-7]*"
        t.type = "NUM_OCT"
        return t

    def t_EXPR_BINNUMBER(self, t):
        r"0b[0-1]*"
        t.type = "NUM_BIN"
        return t

    def t_EXPR_INT(self, t):
        r'\d+'
        t.type = "NUM_INT"
        t.value = int(t.value)
        return t

    @plylex.TOKEN(re_identifier)
    def t_EXPR_ID(self, t):
        t.type = self.reserved.get(t.value.lower(), 'ID')
        return t

    def t_EXPR_LPAREN(self, t):
        r'\('
        t.lexer.paren_level += 1
        return t

    def t_EXPR_RPAREN(self, t):
        r'\)'
        t.lexer.paren_level -= 1
        if t.lexer.paren_level == -1:
            raise_lex_error(t, "Closing bracket error.", type=SyntaxError)
        return t

    def t_EXPR_LARRAY(self, t):
        r'\['
        t.lexer.array_level += 1
        return t

    def t_EXPR_RARRAY(self, t):
        r'\]'
        t.lexer.array_level -= 1
        if t.lexer.array_level == -1:
            raise_lex_error(t, "Closing array error.", type=SyntaxError)
        return t

    def t_EXPR_LDICT(self, t):
        r'\{'
        t.lexer.dict_level += 1
        return t

    def t_EXPR_RDICT(self, t):
        r'\}'
        t.lexer.dict_level -= 1
        if t.lexer.dict_level == -1:
            raise_lex_error(t, "Closing dict error.", type=SyntaxError)
        return t

    def t_EXPR_NEWLINE(self, t):
        r"\n"
        if t.lexer.paren_level == 0 \
            and t.lexer.dict_level == 0 \
                and t.lexer.array_level == 0:
            t.lexer.pop_state()
        return t

    def t_EXPR_WS(self, t):
        r"\s"
        return t

    # - BODY state

    def t_BODY_NEWLINE(self, t):
        r"\n"
        # Set the start if we didn't yet
        if t.lexer.body_start == -1:
            t.lexer.body_start = t.lexer.lexpos
            t.lexer.body_start_lineno = t.lexer.lineno
            t.lexer.body_tokens = t.lexer.computed['text'][t.lexer.lineno - 1][3:]

        starting_indent = t.lexer.computed['indent'][
            t.lexer.body_start_lineno - 1
        ]
        ahead_indent = t.lexer.computed['indent'][t.lineno+1]
        prev_text = t.lexer.computed['text'][t.lineno-1]
        curr_text = t.lexer.computed['text'][t.lineno]
        ahead_text = t.lexer.computed['text'][t.lineno+1]
        close = False
        add = ""

        if t.lexer.body_indent == -1:
            close = False

        if not close and prev_text.startswith("---"):
            if ahead_text.startswith("---"):
                close = True
                tpos = t.lexer.lexpos# + 0 - 1
                add = "0"

        elif not close and ahead_text.startswith("---"):
            close = True
            tpos = t.lexer.lexpos# + 0 - 1

        if not close:
            if ahead_indent < starting_indent:
                if not ahead_text.startswith("---") and ahead_text != "\n":
                    close = True
                    if not curr_text == '\n':
                        tpos = t.lexer.lexpos# + 0 - 1
                        add = "0"
                    else:
                        add = t.lexer.computed['indent'][t.lineno-1]*" " + \
                            t.lexer.computed['text'][t.lineno-1]
                        tpos = t.lexer.lexpos

        if close:
            t.value = bodify_indents(t.lexer.lexdata[t.lexer.body_start:tpos-1],
                                     t.lexer.body_indent
                                     )
            t.type = "BODY"
            t.endline = t.lexer.lineno
            t.lineno = t.lexer.body_start_lineno
            t.lexer.lineno += 1
            t.lexer.lexpos += len(add) or 1
            t.lexer.lexpos -= 1
            t.tokens = t.lexer.body_tokens.split(",")
            t.lexer.body_tokens = None
            t.lexer.body_start = -1
            t.lexer.body_start_lineno = -1
            t.lexer.ahead_indent = -1
            self.stack.pop(True)
            return t
        else:
            # NEWLINE...
            pass

        t.lexer.lineno += 1

    def t_BODY_text(self, t):
        r'.+'

    # - Other
    def t_error(self, t):
        message = "Illegal character '%s' at %s."
        raise_lex_error(t, message % (t.value[0], t.lexpos), type=SyntaxError,)

    t_BODY_error = t_error
    t_BLOCK_error = t_error
    t_EXPR_error = t_error
    t_TRIPLEQ1_error = t_error
    t_TRIPLEQ2_error = t_error
    t_SINGLEQ1_error = t_error
    t_SINGLEQ2_error = t_error

    def t_eof(self, t):
        if t.lexer.lexstate == "BLOCK":
            raise_lex_error(t, "Insufficient Ends", type=SyntaxError,)
        if t.lexer.lexstate in (
            "TRIPLEQ1", "TRIPLEQ2",
            "SINGLEQ1", "SINGLEQ2",
        ):
            raise_lex_error(t, "EOF while scanning string", type=SyntaxError,)

    t_BODY_eof = t_eof
    t_BLOCK_eof = t_eof
    t_EXPR_eof = t_eof
    t_TRIPLEQ1_eof = t_eof
    t_TRIPLEQ2_eof = t_eof
    t_SINGLEQ1_eof = t_eof
    t_SINGLEQ2_eof = t_eof

    # -- Class Functions

    def __init__(self, **kwargs):
        pass

    def __getattr__(self, attr):
        if attr in ("lineno",):
            return self.lexer.lineno

    def build(self, **kwargs):
        """Build the lexer.

        Args:
            `kwargs`:
                `debug`: Whether to use debug mode.
                `enable_colors`: Whether to print with cprint.
                `lex_kwargs`: Dict to use for PLY LEX.
        """
        if 'debug' in kwargs.keys():
            self.debug = kwargs.pop('debug')

        self.COLORS = {x: "" for x,y in printers.COLORS.items()}
        if 'enable_colors' in kwargs.keys():
            if kwargs.pop('enable_colors') == True:
                self.COLORS = printers.COLORS
        if 'lex_kwargs' not in kwargs.keys():
            kwargs['lex_kwargs'] = {}
        self.lexer = plylex.lex(module=self, debug=(self.debug >= 2),
                                **kwargs['lex_kwargs']
                                )
        self.stack = LexStack(lexer=self.lexer, store=[
            {"_indent": 0, "t": None}
        ])
        self.lexer.last_token = None
        self.lexer.source = None
        self.token_stream = None
        self.current_token = None
        self.ps = []

    def token(self):
        try:
            self.p_one = self.current_token
            self.ps.append(self.p_one)
            self.current_token = next(self.token_stream)
            return self.current_token
        except StopIteration:
            return None

    def progress(self, amount):
        l = self.lexer
        ll = l.lineno
        lx = l.computed["lengthx"][ll]
        l.lexpos += amount
        return l.lexpos

    def print_token(self, token, offset=-1):
        C = self.COLORS
        val = C["D"] + str((token.value_quoted \
            if hasattr(token, "value_quoted") else token.value) \
                if token.type != "BODY" else token.value
        )
        val = val.replace("\n", "\\n")
        val = (val[0:71] + "...") if val[0:71] != val else val
        self.print(" " * ( 1
                    + self.lexer.computed["indent"][token.lineno]
                    + (1 if offset == (token.lineno if token.type != "NAME" else 0) else 0)
                ) + C["B"] + "T " + C["C"] + str(token.type) + (" = "
                    + C["D"] + str(val)) if token.value else " = null"
            )

    def get_tokens(self):
        token = self.token()
        result = []
        cline = 0
        while (token != None):
            if token and hasattr(token, "type"):
                result.append(token)
                if (token.type not in ("NEWLINE", "WS",)):
                    self.print_token(token, cline)
                    cline = token.lineno
            token = self.token()
        return result

    def __iter__(self):
        return self.token_stream

    def make_token_stream(self, lexer):
        """Filters for token stream."""
        token_stream = iter(lexer.token, None)
        token_stream = self.filter_strings(lexer, token_stream)
        token_stream = self.post_token(lexer, token_stream)
        return token_stream

    def filter_strings(self, lexer, toks):
        """Filter tokens for strings and create STRING tokens."""
        for tok in toks:
            if not tok.type.startswith("STRING_START_"):
                yield tok
                continue
            start_tok = tok
            string_toks = []
            for tok in toks:
                if tok.type == "STRING_END":
                    break
                else:
                    assert tok.type.startswith("STRING_CONTINUE"), tok.type
                    string_toks.append(tok)
            else:
                # End of for loop
                raise_lex_error(start_tok, "EOF while scanning string",
                                type=SyntaxError,)

            if "SINGLE" in start_tok.type:
                start_tok.lineno = tok.lineno

            start_tok.quotes = start_tok.type[13:]
            start_tok.type = "STRING"
            start_tok.value = convert_string(start_tok, string_toks)
            yield start_tok

    def post_token(self, lexer, toks):
        """Last filter for tokens.

        - Increment newlines lineno.
        - Follow indent for ATTRs
        - Set `last_token`
        - Remove Newline and Whitespace from the stream.
        """
        for tok in toks:
            if not tok:
                if debug:
                    self.print("No tokens found!", "COLERR") # STRING
                break
            if tok.type == "NEWLINE":
                lexer.lineno += 1

            # Token follow checks
            # e.g. Check EXPR's STRINGS and IDs
            if lexer.last_token:
                for check in self.checks_tokens:
                    if lexer.last_token.type.endswith(check["tokens"][0]):
                        if tok.type in check["tokens"][1]:
                            raise_lex_error(tok, check["message"],
                                            type=SyntaxError
                                            )

            if tok.type not in ("WS", "NEWLINE",):
                lexer.last_token = tok

            if tok.type in ("ATTR",):
                self.stack.follow_indent(tok)

            if tok.type not in ("NEWLINE", "WS",):
                yield tok
                continue
            else:
                continue

    def input(self, data, source="<string>"):
        """Create token stream and compute data."""
        data = "\n" + data
        self.token_stream = self.make_token_stream(self.lexer)
        self.lexer.lineno = 0
        self.lexer.e3lm_lexer = self
        self.lexer.input(data)
        self.lexer.source = source
        self.compute_input(data)

    def compute_input(self, text, append="\n"):
        """Apply `compute_pattern` and capture `compute_pattern_inds` into the\
        lexer `computed`.
        """
        # Initialize self.lexer.computed
        try:
            assert self.lexer.computed != None
        except AttributeError:
            self.lexer.computed = {}

        for key in self.compute_pattern_inds:
            if key not in self.lexer.computed.keys():
                self.lexer.computed[key] = []

        text += "\n"  # Extend computed with a new line.

        # Compute matches
        matches = self.compute_pattern.finditer(text)
        count = 0
        for matchNum, match in enumerate(matches):
            for key in self.compute_pattern_inds:
                append = False
                appendKey = key
                appendGroups = self.compute_pattern_inds[key]
                appendNones = False

                if key == "comment":
                    appendNones = True
                elif key == "newline":
                    append = {
                        "text": "!None",
                        "newline": "\n",
                    }
                elif key == "indent":
                    append = {
                        "indent": "spacelen()",
                    }

                for groupNum in range(0, len(match.groups())):
                    groupNum = groupNum + 1
                    group = match.group(groupNum)
                    if groupNum in appendGroups:
                        if append or appendNones or (not appendNones and
                                                     group != None):
                            if append:
                                for ap in append:
                                    if append[ap] == "!None":
                                        if group != None:
                                            self.lexer.computed[ap].append(
                                                group
                                            )
                                    elif append[ap] == "spacelen()":
                                        if group != None:
                                            group = group.replace('\t', ' '*4)
                                            self.lexer.computed[ap].append(
                                                len(group)
                                            )
                                    else:
                                        self.lexer.computed[ap].append(
                                            append[ap]
                                        )
                            else:
                                self.lexer.computed[appendKey].append(group)

            count += 1

        # Compute newline offsets
        offsets = [0]
        for m in self._newline_pattern.finditer(text):
            offsets.append(m.end())

        self.lexer.line_offsets = offsets

        self.lexer.computed["lengthx"] = []
        for m in range(len(self.lexer.computed["text"])):
            x = self.lexer.computed["text"][m]
            y = self.lexer.computed["indent"][m]
            z = self.lexer.computed["comment"][m]
            self.lexer.computed["lengthx"].append(len(x) \
                if x.endswith("\n") else len(x+" "))
            self.lexer.computed["lengthx"][m] += y
            self.lexer.computed["lengthx"][m] += len(z) if z else 0
            

    def find_column(self, input, token):
        """Compute column where `input` is a text string."""
        line_start = input.rfind('\n', 0, token.lexpos) + 1
        return (token.lexpos - line_start) + 1
