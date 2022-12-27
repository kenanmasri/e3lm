var basic_dt = [
    String,
    Number,
    Boolean,
    undefined,
    null,
    Array,
    Object,
]

var tokens = [
    // Expr
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
    // ID
    'ID',
    'DOT',
    'COLON',
    'COMMA',
    // Syntax
    'IMPORT',
    'CLASS',
    'NAME',
    'ATTR',
    'TERM',
    'AVAL',
    'BODY',
    'END',
    // Other
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
];

var regexes = {
    "IMPORT": new RegExp("^([ \\t]*)([iI][mM][pP][oO][rR][tT]\\s+([^ \\t;\\n]+))(;.*)?", "gm"),
    "Floatnumber": new RegExp("(([0-9](?:_?[0-9])*\\.(?:[0-9](?:_?[0-9])*)?|\\.[0-9](?:_?[0-9])*)([eE][-+]?[0-9](?:_?[0-9])*)?|[0-9](?:_?[0-9])*[eE][-+]?[0-9](?:_?[0-9])*)", "g"),
    "Imagnumber": new RegExp("([0-9](?:_?[0-9])*[jJ]|(([0-9](?:_?[0-9])*\\.(?:[0-9](?:_?[0-9])*)?|\\.[0-9](?:_?[0-9])*)([eE][-+]?[0-9](?:_?[0-9])*)?|[0-9](?:_?[0-9])*[eE][-+]?[0-9](?:_?[0-9])*)[jJ])", "g"),
}

module.exports = {
    "regexes": regexes,
    "tokens": tokens,
    "basic_dt": basic_dt,
}