"""
Author: Kenan Masri

"""

import os
import re
import textwrap
from ply import yacc
from e3lm.helpers.printers import _print, cprint
from e3lm.utils.funcs import strip_once
from e3lm.lang import ast
from e3lm.lang.data import tokens, regexes
from e3lm.lang.lexer import E3lmLexer


class E3lmParser():
    """The 3lm language parser."""
    # --- Class variables ---
    debug = False
    tokens = tokens
    scopes = [{
        "last": None,
        "next": None,
        "current": None,
    }]
    print_method = _print
    errors = []

    # --- Rules ---
    precedence = (
        ('left', 'END',),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE'),
    )

    # Indefinite number of blocks under master
    def p_master(self, p):
        '''
        master    : master block
                  | block
        '''
        if len(p) == 3:
            p[1].add(p[2])
            p[0] = p[1]
        else:
            p[0] = ast.Program(imports=self.imports, blocks=[p[1]])

    # Block variations
    def p_block(self, p):
        '''
        block   : CLASS blockcontent END
                | CLASS END
        '''
        if isinstance(p[1], tuple):
            klass = p[1][0]
            name = p[1][1]
        else:
            klass = p[1]
            name = ""
        bcontent = p[3] if len(p) == 5 \
            else p[2] if len(p) == 4 and type(p[2]) == ast.BlockContent \
            else None

        b = ast.Block(klass, children=bcontent)
        b.name = name
        p[0] = b

    # Block Content of other blocks and attrs
    def p_blockcontent(self, p):
        '''
        blockcontent    : blockcontent attr
                        | blockcontent block
                        | attr
                        | block
        '''
        if len(p) == 3:
            p[0] = p[1]
            p[0].children = p[1].children
            if p[2].name not in [a.name for a in p[0].children
                                 if type(a) == ast.Attr]:
                p[0].children.extend([p[2]])
            else:
                self.errors.append([
                    (AttributeError, p.lexpos(2),
                     p.lexer.lexer.last_token.lineno-1),
                    "Duplicate attribute '%s'" % p[2].name, p,
                ])
        else:
            p[0] = ast.BlockContent([p[1]])

    # Body and attrs
    def p_attrset(self, p):
        '''attr     : ATTR expr
                    | BODY
        '''
        if len(p) > 2:
            p[0] = ast.Attr(p[1], p[2])
        else:
            p[0] = ast.Attr("body", p[1],
                            tokens=p.lexer.p_one.tokens or [])

    # binary operations
    def p_binops(self, p):
        ''' expr    : expr PLUS term
                    | expr MINUS term
                    | term
            term    : term TIMES factor
                    | term DIVIDE factor
                    | term TIMES TIMES factor
                    | term DIVIDE DIVIDE factor
                    | factor
        '''
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 5:
            if p[2] == "*" and p[3] == "*":
                op = "**"
            elif p[2] == "/" and p[3] == "/":
                op = "//"
            p[0] = ast.BinOp(op, p[1], p[4])
        else:
            p[0] = ast.BinOp(p[2], p[1], p[3])

    # Number + unary as factors
    def p_factor_num(self, p):
        '''factor : NUM_INT
                  | NUM_FLOAT
                  | NUM_HEX
                  | NUM_OCT
                  | NUM_IMAG
                  | NUM_BIN
                  | PLUS factor
                  | MINUS factor
        '''
        if p[1] in ("+", "-"):
            p[0] = ast.UnaryOp(p[1], p[2])
        else:
            p[0] = ast.Num(p.lexer.p_one.value, p.lexer.p_one.type)

    # parenthesis expr as factor
    def p_factor_paren_expr(self, p):
        '''factor : LPAREN expr RPAREN
        '''
        p[0] = p[2]

    # Strings as factor
    def p_factor_str(self, p):
        '''factor : STRING
        '''
        p[0] = ast.Str(p[1])
        p[0].type = p.lexer.p_one.quotes

    def p_factor_bool(self, p):
        '''factor : BOOL
        '''
        p[0] = ast.Bool(p[1])

    def p_factor_none(self, p):
        '''factor : NONE
        '''
        p[0] = ast.Undefined(p[1])

    # Identifier as factor
    def p_factor_id(self, p):
        '''factor : identifier
                  | func
        '''
        p[0] = p[1]

    def p_func(self, p):
        '''func   : ID LPAREN funcargs RPAREN
                  | ID LPAREN RPAREN
        '''
        if len(p) == 5:
            p[0] = ast.Func(p[1], p[3])
        else:
            p[0] = ast.Func(p[1], [])

    def p_funcargs(self, p):
        '''funcargs : funcargs COMMA expr
                    | expr
        '''
        if len(p) == 4:
            p[0] = p[1]
            p[0].add(p[3])
        else:
            p[0] = ast.FuncArgs([p[1]])

    def p_id_func(self, p):
        '''identifier : factor DOT func
                      | identifier DOT func
        '''
        p[0] = ast.Identifier([p[1], p[3]])

    def p_id(self, p):
        '''identifier : identifier DOT ID
                      | factor DOT ID
                      | func
                      | ID
        '''
        if len(p) == 4:
            if type(p[1]) == ast.Identifier:
                p[0] = p[1]
                p[0].add(p[3])
            else:
                p[0] = ast.Identifier([p[1], p[3]])
        else:
            p[0] = ast.Identifier([p[1]])

    def p_id_index(self, p):
        '''identifier : identifier LARRAY expr RARRAY
        '''
        p[0] = p[1]
        p[0].add(ast.Index(p[3]))

    # Arraydata additions
    def p_arraydata(self, p):
        '''arraydata : arraydata COMMA expr
                     | expr
        '''
        if len(p) == 4:
            p[0] = p[1]
            p[0].add(p[3])
        else:
            p[0] = ast.Array([p[1], ])

    # Basic array syntax
    def p_factor_arr(self, p):
        '''factor : LARRAY arraydata RARRAY
                  | LARRAY arraydata COMMA RARRAY
                  | LARRAY RARRAY
        '''
        if len(p) == 3:
            p[0] = ast.Array([])
        else:
            p[0] = p[2]

    # Dict additions
    def p_dictdata(self, p):
        '''dictdata : dictdata COMMA dictcouple
                    | dictcouple
        '''
        if len(p) == 4:
            p[0] = p[1]
            p[0].add(p[3])
        else:
            p[0] = ast.DictData([p[1]])

    def p_not(self, p):
        '''expr : NOT expr
        '''
        p[0] = ast.UnaryOp('!', p[1])

    def p_dict_dictdata(self, p):
        '''dictdata : dict
        '''
        p[0] = p[1]

    def p_factor_dictcouple(self, p):
        '''dictcouple : expr COLON expr
        '''
        p[0] = ast.DictCouple(p[1], p[3])

    def p_factor_dict(self, p):
        '''dict   : LDICT dictdata RDICT
                  | LDICT dictdata COMMA RDICT
                  | LDICT RDICT
        '''
        p[0] = ast.Dict(p[2]) if len(p) != 3 else ast.Dict()

    def p_dict(self, p):
        '''factor : dict
        '''
        p[0] = p[1]

    def p_error(self, p):
        if p:
            # curimport = self.srs
            # for key,val in self.imports.items():
            #     if val[0] <= p.lineno <= val[1]:
            #         curimport = key

            # lineno = p.lineno if curimport == self.srs \
            #     else p.lineno - self.imports[curimport][0]

            self.errors.append([
                (SyntaxError, p.lexpos, p.lineno), "Syntax error near token "
                + str(p), p,
            ])
            # self.parser.errok()
        else:
            self.print_method("Syntax error at EOF", "ERROR")

    # --- Functions ---
    # -- Class functions

    def build(self, **kwargs):
        if 'debug' in kwargs.keys():
            self.debug = kwargs.pop('debug')
        self.print_method = _print
        if 'enable_colors' in kwargs.keys():
            if kwargs.pop('enable_colors') == True:
                self.print_method = cprint
        if 'lexer' in kwargs.keys():
            self.e3lmLexer = kwargs.pop('lexer')
        else:
            self.e3lmLexer = E3lmLexer()
            if 'lexer_kwargs' in kwargs.keys():
                lwargs = kwargs['lexer_kwargs']
            else:
                lwargs = {}
            self.e3lmLexer.build(**lwargs)
        self.tokens = self.e3lmLexer.tokens
        if 'yacc_kwargs' not in kwargs.keys():
            kwargs['yacc_kwargs'] = {}
        self.parser = yacc.yacc(module=self, debug=(self.debug >= 2),
                                **kwargs['yacc_kwargs']
                                )
        self.parser.e3lm_parser = self
        self.parser.last_node = None
        if 'tracking' in kwargs['yacc_kwargs'].keys():
            self.tracking = kwargs['yacc_kwargs']['tracking']
        else:
            if 'tracking' in kwargs.keys():
                self.tracking = kwargs['tracking']
            else:
                self.tracking = False
        self.errors = []

    def parse(self, input, source=None, **kwargs):
        # get curpath for imports
        is_file = False

        if input.count("\n") == 0 and os.path.exists(input):
            is_file = True
            self.srs = os.path.abspath(input)
            self.curpath = self.srs
            source = input

        self.srs = "<string>"
        if source:
            if os.path.exists(source):
                self.srs = os.path.abspath(source)
                self.curpath = self.srs

        if not is_file:
            textinput = input
            self.curpath = os.getcwd()
        else:
            self.curpath = os.path.dirname(os.path.abspath(input))
            with open(self.srs, 'r', encoding='utf-8') as f:
                textinput = "".join(f.readlines())

        # Before parsing-and-lexing filters
        textinput = self.do_imports(textinput)
        result = self.parser.parse(textinput, self.e3lmLexer, **kwargs)

        if self.debug >= 1:
            if len(self.errors) > 0:
                for err in self.errors:
                    if ('tracking' in kwargs.keys() and kwargs['tracking']) \
                            or self.tracking:
                        self.print_method((err[0], err[1]), "ERROR")
                    else:
                        self.print_method((err[1]), "ERROR")
        return result

    def do_imports(self, text):
        """Regex the import statements from `input` and load them."""
        curpath = os.path.dirname(self.srs)

        def get_file(fname):
            """Check for `fname` existence relative to main file dir (or
            cwd)."""
            fname = strip_once(fname, "\"\'")
            filename, fileext = os.path.splitext(fname)
            if not fileext:
                fname = fname + ".3lm"
            fpath = curpath + os.path.sep + fname
            if not os.path.exists(fpath):
                fpath = os.path.abspath(fname)
                if not os.path.exists(fpath):
                    raise Exception("'{}' does not exist.".format(fpath))
            return fpath

        regex = regexes["IMPORT"]
        data = text.splitlines(True)
        self.imports = {}
        curimport = self.srs
        _lastcurimport = self.srs
        linecounter = {self.srs: 0, }
        for lineno, line in enumerate(data):
            curimport = self.srs
            for key, val in self.imports.items():
                if val[0] <= lineno <= val[1]:
                    curimport = key

            if _lastcurimport != curimport:
                _lastcurimport = curimport
                linecounter[curimport] = 0

            linecounter[curimport] += 1
            match = re.match(regex, line)
            if match:
                m = match.group(3)
                fpath = get_file(m)
                if fpath in self.imports.keys():
                    raise SyntaxError(
                        "Importing '{}' again.".format(
                            os.path.basename(fpath)
                        ),
                        (curimport,
                            linecounter[curimport]+1, match.end(1), line
                         )
                    )
                with open(fpath, "r", encoding='utf-8') as f:
                    new = f.readlines()
                new.append("\n")
                self.imports[fpath] = (lineno+1, lineno+len(new))
                data[lineno] = ""
                for i, l in enumerate(new):
                    data.insert(lineno+i, l)

        return "".join(data)
