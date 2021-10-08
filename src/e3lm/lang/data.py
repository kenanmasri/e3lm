"""
Author: Kenan Masri

Tokens for the E3lmLexer and E3lmParser.
Regexes for the E3lmLexer and E3lmParser.
"""

basic_dt = (complex, str, int, float, bool, list, dict, tuple,)

tokens = (
    # Expr
    'BOOL',
    'NONE',
    'NUM_IMAG',
    'NUM_FLOAT',
    'NUM_HEX',
    'NUM_OCT',
    'NUM_INT',
    'NUM_BIN',
    'UNIT',
    'PLUS',
    'MINUS',
    'TIMES',
    'DIVIDE',
    'LPAREN',
    'RPAREN',
    'AND',
    'OR',
    'NOT',
    'LARRAY',
    'RARRAY',
    'LDICT',
    'RDICT',
    # ID
    'ID',
    'DOT',
    'COLON',
    'COMMA',
    # Syntax
    'IMPORT',
    'CLASS',
    'NAME',
    'ATTR',
    'TERM',
    'AVAL',
    'BODY',
    'END',
    # Other
    'WS',
    'NEWLINE',
    'COMMENT',
    'STRING_START_SINGLEQ1',
    'STRING_START_SINGLEQ2',
    'STRING_START_TRIPLEQ1',
    'STRING_START_TRIPLEQ2',
    'STRING_CONTINUE_NEWLINE',
    'STRING_CONTINUE',
    'STRING_END',
    'STRING',
)

regexes = {
    "IMPORT": r"^([ \t]*)([iI][mM][pP][oO][rR][tT][ \t]+([^ \t;\n]+))(?=[ ;])?",
}
