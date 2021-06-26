// lexer.js

const langdata = require("./data");
// var Lexer = require('flex-js');
var Tokenizr = require('tokenizr');
const { default: Complex } = require("complex.js");
const tokens = langdata.tokens;
const regexes = langdata.regexes;

const Generator =
  {
    map: (f,g) => function* (...args)
      {
        for (const x of g (...args))
          yield f (x)
      },
    filter: (f,g) => function* (...args)
      {
        for (const x of g (...args))
          if (f (x))
            yield x
      }
  }


class LexStack extends Object {
    id = 0;
    lexer = null;

    constructor(lexer=null, store=[], follow_indentation=true) {
        super(lexer, store, follow_indentation);
        this.store = store;
        this.lexer = lexer;
        this.follow_indentation = follow_indentation;
        return this;
    }

    push(t, stack={}, lexstate=null) {
        if (typeof stack !== "object") {
            throw Error("Pushed stacks must be Object.");
        }

        stack["t"] = t;

        // New stack will have an _indent_gt. This is the len of the computed
        // Indents of the token line.
        // This number will be compared to be GREATER THAN "current" tokens...
        if (this.follow_indentation) {
            stack["_indent_gt"] = this.lexer.computed["indent"][t.lineno];
        }

        this.store = []
        this.store.push(stack);
        this.id = this.store.length - 1;

        if (lexstate != null) {
            this.lexer.push_state(lexstate);
        }

        return this.id;
    }

    pop(poplex=false) {
        if (poplex) {
            this.lexer.pop_state();
        }
        var stack = this.store.pop();
        this.id -= 1;

        return stack;
    }

    follow_indent(t, val=null) {
        var lineno = t.lineno - 1;
        var indents = this.lexer.computed["indents"][lineno];
        if (this.hasOwnProperty("_indent_gt")) {
            var req_indents = this._indent_gt;
            this.update("_indent", req_indents);
            indents = this._indent;
            delete this.store[this.id]["_indent_gt"];
        } else {
            req_indents = this._indent;
        }

        if (val) {
            this.update('_indent', val);
        }

        if (req_indents != indents) {
            raise_lex_error(t, "Expected " + String(req_indents) + " indents, got " + String(indents) + ".",
            type="IndentationError",
            details={
                "req_indents": req_indents,
                "indents": indents,
                }
            );
        }
    }

    update(key, value, id=null) {
        if (id == null) {
            id = this.id;
        }
        if (this.store.length == 0) {
            this.store = [{}];
        }

        if (!(key in this.store[id])) {
            if (value == "++" || value == "--") {
                this.store[id][key] = 0;
            }
        }

        if (value == "++") {
            value = this.store[id][key] + 1;
        } else if (value == "--") {
            value = this.store[id][key] - 1;
        }

        this.store[id][key] = value;
    }

    get(key, defaultval=null, id=null) {
        if (id == null) { id = this.id; }
        if (this.hasOwnProperty(key)) {
            var r = this[key];
        }
        if (defaultval != null) {
            var r = defaultval;
        }

        if (this.store[id].hasOwnProperty(key)) {
            return this.store[id][key];
        } else {
            return r;
        }
    }
}

Object.defineProperty(LexStack, "length", {
    get: function() {
        return this.store.length;
    }
});

class E3lmLexer {

    compute_pattern = /(([ \t]*)(.*)(;.*)\n?)|(([ \t]*)\n)|(([ \t]*)(.+)\n?)/mg;
    compute_pattern_inds = {
        "indent": [2, 6, 8,],
        "text": [3, 9,],
        "comment": [4,],
        "newline": [5,],
    }

    _newline_pattern = /\n/g;
    
    debug = true
    // print_method = console.log
    default_state = 'default';
    
    states = [
        ["BLOCK", "exclusive"],
        ["BODY",  "exclusive"],
        ["EXPR",  "exclusive"],
        ["SINGLEQ1", "exclusive"],
        ["SINGLEQ2", "exclusive"],
        ["TRIPLEQ1", "exclusive"],
        ["TRIPLEQ2", "exclusive"],
    ]

    reserved = {
        'end': 'END',
        'true': 'BOOL',
        'false': 'BOOL',
        'none': 'NONE',
    }

    tokens = tokens

    digit_char = "[0-9]"
    nondigit_char = "[_\-A-Za-z]"
    uppercased_char = "[A-Z]"
    begin_char_up = "[_A-Z]"
    begin_char = "[_A-Za-z]"
    cont_char = "[_A-Za-z0-9]"
    any_char = "."
    identifier_char = this.begin_char + this.cont_char
    class_name_char = this.begin_char_up + this.cont_char

    re_identifier = new RegExp('(' + this.identifier_char + '*)', 'y');
    re_class_def = new RegExp('(' + this.class_name_char + "* " +
        this.identifier_char + "*)", 'y');
    
    re_attr = new RegExp('(' + this.identifier_char + '*' + "\\s?\=\\s?)", 'y')

    re_float = regexes["Floatnumber"];

    t_EXPR_PLUS = /\+/g
    t_EXPR_MINUS = /-/g
    t_EXPR_TIMES = /\*/g
    t_EXPR_DIVIDE = /\//g
    t_EXPR_AND = /\&/g
    t_EXPR_OR = /\|/g
    t_EXPR_NOT = /\!/g
    t_EXPR_COLON = /\:/g
    t_EXPR_DOT = /\./g
    t_EXPR_COMMA = /\,/g

    check_tokens = [
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
    ];

    // Ignores
    t_ignore_COMMENT = /[ \t]*\;(.*)/g
    t_ignore_IMPORT = regexes["IMPORT"]

    // -- States --
    // Ignores
    t_BLOCK_ignore_COMMENT = this.t_ignore_COMMENT
    t_EXPR_ignore_COMMENT = this.t_ignore_COMMENT
    // supress PLY warning
    t_TRIPLEQ1_ignore = ""
    t_TRIPLEQ2_ignore = ""
    t_SINGLEQ1_ignore = ""
    t_SINGLEQ2_ignore = ""


    constructor() {
        this.tokenizr = new Tokenizr;
        this.stack = new LexStack(this, [{"_indent":0,"t":null}]);
        this.define_tokenizr_rules();
        return this;
    }

    define_tokenizr_rules = () => {
        
        // this.tokenizr.rule(state, pattern, function, name)

        this.tokenizr.after( (ctx,match,rule) => {
            
        });

        //#region State: EXPR
        this.tokenizr.rule('EXPR', this.t_EXPR_PLUS, (ctx, match) => {
            ctx.accept('PLUS');
        }, 'rule_EXPR_PLUS');
        
        this.tokenizr.rule('EXPR', this.t_EXPR_MINUS, (ctx, match) => {
            ctx.accept('MINUS');
        }, 'rule_EXPR_MINUS');

        this.tokenizr.rule('EXPR', this.t_EXPR_TIMES, (ctx, match) => {
            ctx.accept('TIMES');
        }, 'rule_EXPR_TIMES');

        this.tokenizr.rule('EXPR', this.t_EXPR_DIVIDE, (ctx, match) => {
            ctx.accept('DIVIDE');
        }, 'rule_EXPR_DIVIDE');

        this.tokenizr.rule('EXPR', this.t_EXPR_AND, (ctx, match) => {
            ctx.accept('AND');
        }, 'rule_EXPR_AND');

        this.tokenizr.rule('EXPR', this.t_EXPR_OR, (ctx, match) => {
            ctx.accept('OR');
        }, 'rule_EXPR_OR');

        this.tokenizr.rule('EXPR', this.t_EXPR_NOT, (ctx, match) => {
            ctx.accept('NOT');
        }, 'rule_EXPR_NOT');

        this.tokenizr.rule('EXPR', this.t_EXPR_COLON, (ctx, match) => {
            ctx.accept('COLON');
        }, 'rule_EXPR_COLON');

        this.tokenizr.rule('EXPR', this.t_EXPR_DOT, (ctx, match) => {
            ctx.accept('DOT');
        }, 'rule_EXPR_DOT');

        this.tokenizr.rule('EXPR', this.t_EXPR_COMMA, (ctx, match) => {
            ctx.accept('COMMA');
        }, 'rule_EXPR_COMMA');
        
        //#endregion

        //#region Main

        // State: INITIAL

        this.tokenizr.rule(this.default_state, /\n/g, (ctx, match) => {
            ctx.accept('NEWLINE');
        }, 'rule_NEWLINE');

        this.tokenizr.rule(this.default_state, this.re_class_def, (ctx, match) => {
            ctx.push('BLOCK');
            ctx.accept('CLSS', match[0]);
        }, 'rule_CLSS');

        this.tokenizr.rule(this.default_state, this.re_identifier, (ctx, match) => {
            var type = 'ID';
            if (match[0].toLowerCase() in this.reserved) {type = this.reserved[match[0].toLowerCase()];}
            ctx.accept(type);
        }, 'rule_ID');

        // State: BLOCK

        this.tokenizr.rule('BLOCK', /[eE][nN][dD](.*)/g, (ctx, match) => {
            ctx.accept('END').pop();
            ctx.data('check_indents', true);
            this.stack.pop();
            this.stack.indent_check = "lt"
        }, 'rule_BLOCK_END');

        this.tokenizr.rule('BLOCK', this.re_attr, (ctx, match) => {
            // Remove the equals part by getting the captured value only.
            var value = match[4];
            var type = 'ATTR';
            if (match[0].toLowerCase() in this.reserved) {
                type = this.reserved[match[0].toLowerCase()];
            }
            if (type != 'ATTR') {this.raise_error(ctx, 'SyntaxError', "Encountered reserved keyword");};
            ctx.push('EXPR');
            ctx.data('paren_level', 0);
            ctx.data('dict_level', 0);
            ctx.data('array_level', 0);
            var lineno = ctx.info().lineno;
            this.stack.update('_indent', this.computed["indent"][lineno]);
            ctx.accept(type, value);
        }, 'rule_BLOCK_ATTR');

        this.tokenizr.rule('BLOCK', /\-\-\-/g, (ctx, match) => {
            if (this.tokenizr._pending.length > 0) {
                if (this.last_token.type == "BODY") {
                    ctx.skip(1);
                    ctx.lineno = ctx.lineno + 1;
                    return
                }
            }
            ctx.data('body_start', -1);
            ctx.data('body_start_lineno', -1);
            var lineno = ctx.lineno;
            ctx.data('body_indent', this.computed["indent"][lineno + 1])
            var nfo = ctx.info();
            var t = {
                type: "BODYOPEN",
                value: "",
                pos: nfo.pos,
                lineno: nfo.lineno,
                len: nfo.len,
                col: nfo.col,
            };
            this.stack.push(t, {}, "BODY");
        }, 'rule_BLOCK_BODYOPEN');

        this.tokenizr.rule('BLOCK', /[ \t]/g, (ctx, match) => {
            ctx.accept('WS');
        }, 'rule_BLOCK_WS');

        this.tokenizr.rule('BLOCK', this.re_class_def, (ctx, match) => {
            ctx.push('BLOCK');
            ctx.accept('CLSS', match[0]);
        }, 'rule_BLOCK_CLSS');

        this.tokenizr.rule('BLOCK', this.re_identifier, (ctx, match) => {
            var nfo = ctx.info();
            var t = {
                type: "NAME",
                value: match[0],
                pos: nfo.pos,
                lineno: nfo.lineno,
                len: nfo.len,
                col: nfo.col,
            };
            this.stack.push(t, {});
            this.stack.indent_check = "gt"
            ctx.accept(t.type, t.value);
        }, 'rule_BLOCK_NAME');

        this.tokenizr.rule('BLOCK', /\n/g, (ctx, match) => {
            if (this.tokenizr._pending.length > 0) {
                if (this.last_token.type == "CLSS") {
                    this.stack.push(this.last_token, {});
                    this.stack.indent_check = "gt"
                } else if (this.last_token.type == "NAME") {
                    // Do nothing
                }
            }
            ctx.accept('NEWLINE');
        }, 'rule_BLOCK_NEWLINE');

        // State: EXPR

        this.tokenizr.rule('EXPR', /\\\n/g, (ctx, match) => {
            ctx.lineno += 1;
        }, 'rule_EXPR_escape');

        this.tokenizr.rule('EXPR', /\\(.|\n)/g, (ctx, match) => {
            var type;
            if (match[0] == "\\\n") {
                type = "STRING_CONTINUE_NEWLINE";
            } else {
                type = "STRING_CONTINUE";
            }
            this.tokenizr.lineno += match[0].split("\n").length - 1;
            ctx.accept(type)
        }, 'rule_SQ1_SQ2_TQ1_TQ2_escapes');
        //#endregion

        //#region Stings

        //#region TRIPLEQ1
        this.tokenizr.rule('EXPR', /[bB]?'''/g, (ctx, match) => {
            ctx.push('TRIPLEQ1')
            var type = "STRING_START_TRIPLEQ1"
            if (match[0].includes("r") || match[0].includes("R")) {
                ctx.data("string_raw", true);
            } else {
                ctx.data("string_raw", false);
            }
            var value = match[0].split("'", 1)[0]
            ctx.accept(type, value);
        }, 'rule_EXPR_start_str_TQ1');

        // State: TRIPLEQ1

        this.tokenizr.rule('TRIPLEQ1', /[^'\\]+/g, (ctx, match) => {
            ctx.lineno += match[0].split("\n").length - 1;
            ctx.accept("STRING_CONTINUE");
        }, 'rule_TRIPLEQ1_simple');

        this.tokenizr.rule('TRIPLEQ1', /'(?!'')/g, (ctx, match) => {
            ctx.accept("STRING_CONTINUE");
        }, 'rule_TRIPLEQ1_q1_not_triple');

        this.tokenizr.rule('TRIPLEQ1', /'''/g, (ctx, match) => {
            ctx.accept("STRING_END");
            ctx.pop();
            ctx.data('string_raw', false);
        }, 'rule_TRIPLEQ1_end');

        //#endregion
        
        //#region TRIPLEQ2
        this.tokenizr.rule('EXPR', /[bB]?"""/g, (ctx, match) => {
            ctx.push('TRIPLEQ2')
            var type = "STRING_START_TRIPLEQ2"
            if (match[0].includes("r") || match[0].includes("R")) {
                ctx.data("string_raw", true);
            } else {
                ctx.data("string_raw", false);
            }
            var value = match[0].split('"', 1)[0]
            ctx.accept(type, value);
        }, 'rule_EXPR_start_str_TQ2');

        // State: TRIPLEQ2

        this.tokenizr.rule('TRIPLEQ2', /[^"\\]+/g, (ctx, match) => {
            ctx.lineno += match[0].split("\n").length - 1;
            ctx.accept("STRING_CONTINUE");
        }, 'rule_TRIPLEQ2_simple');

        this.tokenizr.rule('TRIPLEQ2', /"(?!"")/g, (ctx, match) => {
            ctx.accept("STRING_CONTINUE");
        }, 'rule_TRIPLEQ2_q2_not_triple');

        this.tokenizr.rule('TRIPLEQ2', /"""/g, (ctx, match) => {
            ctx.accept("STRING_END");
            ctx.pop();
            ctx.data('string_raw', false);
        }, 'rule_TRIPLEQ2_end');

        //#endregion

        //#region SINGLEQ1
        this.tokenizr.rule('EXPR', /[bB]?"/g, (ctx, match) => {
            this.tokenizr.push('SINGLEQ1')
            var type = "STRING_START_SINGLEQ1"
            if (match[0].includes("r") || match[0].includes("R")) {
                this.tokenizr.data("string_raw", true);
            } else {
                this.tokenizr.data("string_raw", false);
            }
            var value = match[0].split('"', 1)[0]
            ctx.accept(type, value);
        }, 'rule_EXPR_start_str_SQ1');

        // State: SINGLEQ1

        this.tokenizr.rule('SINGLEQ1', /[^"\\\n]+/g, (ctx, match) => {
            ctx.accept("STRING_CONTINUE");
        }, 'rule_SINGLEQ1_simple');

        this.tokenizr.rule('SINGLEQ1', /"/g, (ctx, match) => {
            ctx.accept("STRING_END");
            ctx.pop();
            ctx.data('string_raw', false);
        }, 'rule_SINGLEQ1_end');
        //#endregion
        
        //#region SINGLEQ2
        this.tokenizr.rule('EXPR', /[bB]?'/g, (ctx, match) => {
            this.tokenizr.push('SINGLEQ2')
            var type = "STRING_START_SINGLEQ2"
            if (match[0].includes("r") || match[0].includes("R")) {
                this.tokenizr.data("string_raw", true);
            } else {
                this.tokenizr.data("string_raw", false);
            }
            var value = match[0].split("'", 1)[0]
            ctx.accept(type, value);
        }, 'rule_EXPR_start_str_SQ2');

        // State: SINGLEQ2

        this.tokenizr.rule('SINGLEQ2', /[^'\\\n]+/g, (ctx, match) => {
            ctx.accept("STRING_CONTINUE");
        }, 'rule_SINGLEQ2_simple');

        this.tokenizr.rule('SINGLEQ2', /'/g, (ctx, match) => {
            ctx.accept("STRING_END");
            ctx.pop();
            ctx.data('string_raw', false);
        }, 'rule_SINGLEQ2_end');
        //#endregion

        //#endregion

        //#region EXPR cont'd
        this.tokenizr.rule('EXPR', regexes.Imagnumber, (ctx, match) => {
            var value = new Complex(String(match[0]));
            ctx.accept("NUM_IMAG", value);
        }, 'rule_EXPR_IMAGNUMBER');

        this.tokenizr.rule('EXPR', this.re_float, (ctx, match) => {
            ctx.accept("NUM_FLOAT", Number(match[0]));
        }, 'rule_EXPR_FLOAT');

        this.tokenizr.rule('EXPR', /0[xX][0-9a-fA-F]+?/g, (ctx, match) => {
            ctx.accept('NUM_HEX');
        }, 'rule_EXPR_HEXNUMBER');

        this.tokenizr.rule('EXPR', /0o[0-7]*/g, (ctx, match) => {
            ctx.accept('NUM_OCT');
        }, 'rule_EXPR_OCTNUMBER');

        this.tokenizr.rule('EXPR', /0b[0-1]*/g, (ctx, match) => {
            ctx.accept('NUM_BIN');
        }, 'rule_EXPR_BINNUMBER');

        this.tokenizr.rule('EXPR', /\d+/g, (ctx, match) => {
            ctx.accept('NUM_INT');
        }, 'rule_EXPR_INT');

        this.tokenizr.rule('EXPR', this.re_identifier, (ctx, match) => {
            var type = 'ID';
            if (match[0].toLowerCase() in this.reserved) {type = this.reserved[match[0].toLowerCase()];}
            ctx.accept(type);
        }, 'rule_EXPR_ID');

        this.tokenizr.rule('EXPR', /\(/g, (ctx, match) => {
            ctx.accept('LPAREN');
            var paren_level = ctx.data("paren_level");
            ctx.data("paren_level", paren_level + 1);
        }, 'rule_EXPR_LPAREN');

        this.tokenizr.rule('EXPR', /\)/, (ctx, match) => {
            ctx.accept('RPAREN');
            var paren_level = ctx.data("paren_level");
            if (paren_level == 0) {
                this.raise_error(ctx, "SyntaxError", "Closing bracket error.");
            }
            ctx.data("paren_level", paren_level - 1);
        }, 'rule_EXPR_RPAREN');

        this.tokenizr.rule('EXPR', /\[/g, (ctx, match) => {
            ctx.accept('LARRAY');
            var array_level = ctx.data("array_level");
            ctx.data("array_level", array_level + 1);
        }, 'rule_EXPR_LARRAY');

        this.tokenizr.rule('EXPR', /\]/g, (ctx, match) => {
            ctx.accept('RARRAY');
            var array_level = ctx.data("array_level");
            if (array_level == 0) {
                this.raise_error(ctx, "SyntaxError", "Closing bracket error.");
            }
            ctx.data("array_level", array_level - 1);
        }, 'rule_EXPR_RARRAY');

        this.tokenizr.rule('EXPR', /\{/g, (ctx, match) => {
            ctx.accept('LDICT');
            var dict_level = ctx.data("dict_level");
            ctx.data("dict_level", dict_level + 1);
        }, 'rule_EXPR_LDICT');

        this.tokenizr.rule('EXPR', /\}/g, (ctx, match) => {
            ctx.accept('RDICT');
            var dict_level = ctx.data("dict_level");
            if (dict_level == 0) {
                this.raise_error(ctx, "SyntaxError", "Closing bracket error.");
            }
            ctx.data("dict_level", dict_level - 1);
        }, 'rule_EXPR_RDICT');

        this.tokenizr.rule('EXPR', /\n/g, (ctx, match) => {
            var paren_level = ctx.data('paren_level');
            var array_level = ctx.data('array_level');
            var dict_level = ctx.data('dict_level');
            if (paren_level == 0 && array_level == 0 && dict_level == 0) {
                ctx.pop();
            }
            ctx.accept('NEWLINE');
        }, 'rule_EXPR_NEWLINE');

        this.tokenizr.rule('EXPR', /\s/g, (ctx,m) => {ctx.accept("WS")}, 'rule_EXPR_WS');
        //#endregion

        //#region STATE BODY and eof/error

        // State: BODY
        this.tokenizr.rule('BODY', /\n/g, (ctx, match) => {
            var body_start = ctx.data('body_start');
            var body_start_lineno = ctx.data('body_start_lineno');
            var body_indent = ctx.data('body_indent');
            var nfo = ctx.info();
            var body_tokens = "";

            if (body_start == -1) {
                body_start = nfo.pos; ctx.data('body_start', body_start);
                body_start_lineno = nfo.lineno; ctx.data('body_start_lineno', body_start_lineno);
                body_tokens = this.computed['text'][body_start_lineno].slice(3);
                ctx.data('body_tokens', body_tokens);
            }

            var starting_indent = this.computed['indent'][body_start_lineno];
            var ahead_indent = this.computed['indent'][body_start_lineno + 1];
            var prev_text = this.computed['text'][body_start_lineno - 1];
            var curr_text = this.computed['text'][body_start_lineno];
            var ahead_text = this.computed['text'][body_start_lineno + 1];
            var close = false;
            var add = "";

            if (body_indent == -1) {
                close = false;
            }

            var tpos;
            if (!close && prev_text.startsWith("---")) {
                if (ahead_text.startsWith("---")) {
                    close = true;
                    tpos = nfo.pos + 0 - 1;
                    add = "0";
                }
            } else if (!close && ahead_text.startsWith("---")) {
                close = true;
                tpos = nfo.pos + 0 - 1;
            }

            if (!close) {
                if (ahead_indent < starting_indent) {
                    if (ahead_text.startsWith("---") != true && ahead_text != "\n") {
                        close = true;
                        if (curr_text != "\n") {
                            tpos = nfo.pos + 0 - 1;
                            add = "0";
                        } else {
                            add = this.computed["indent"][nfo.lineno-1] + " " + this.computed["text"][nfo.lineno-1];
                            tpos = nfo.pos;
                        }
                    }
                }
            }

            if (close) {
                var bvalue = bodify_indents(this.lexdata.slice(body_start, tpos), body_indent)
                var type = "BODY";
                var btokens = body_tokens.split(",");
                ctx.pop();
                ctx.lineno += 1;
                ctx.pos -= 1;
                var _skip = add.length; if (_skip == 0) _skip = 1;
                ctx.skip(_skip);
                ctx.data("body_order", -1);
                ctx.accept(type, {
                    "start_lineno": body_start_lineno,
                    "value": bvalue,
                    "tokens": btokens,
                });
                ctx.data("body_tokens", null);
            }
            ctx.lineno += 1;
        })

        this.tokenizr.rule('BODY', /.+/g, (ctx,match) => {
            //
        }, 'rule_BODY_text');

        //#endregion

        //this.tokenizr.rule('EXPR', regexes.Imagnumber, (ctx, match) => {
        //}, 'rule_EXPR_escape');

        //#endregion

        this.tokenizr.rule(this.default_state, this.t_ignore_COMMENT, (ctx, match) => {
            ctx.ignore();
        }, 'rule_ignore_COMMENT');
        this.tokenizr.rule(this.default_state, this.t_ignore_IMPORT, (ctx, match) => {
            ctx.ignore();
        }, 'rule_ignore_IMPORT');
        this.tokenizr.rule('BLOCK', this.t_BLOCK_ignore_COMMENT, (ctx, match) => {
            ctx.ignore();
        }, 'rule_BLOCK_ignore_COMMENT');
        this.tokenizr.rule('EXPR', this.t_EXPR_ignore_COMMENT, (ctx, match) => {
            ctx.ignore();
        }, 'rule_EXPR_ignore_COMMENT');

        this.tokenizr.finish( (ctx) => {
            var state = ctx.state();
            if (state == "BLOCK") {
                this.raise_error(ctx, "SyntaxError", "Insufficient Ends");
            }
            if (["TRIPLEQ1", "TRIPLEQ2", "SINGLEQ1", "SINGLEQ2"].includes(state)) {
                this.raise_error(ctx, "SyntaxError", "EOF While scanning a string");
            }
        });
    }

    raise_error = (ctx, type="LexError", message="") => {
        if (typeof ctx == Tokenizr) {
            var info = ctx.info();
            throw Error(type+"!", info.lineno);
        } else if (ctx.hasOwnProperty("value")) { // It's a token
            throw Error(type+ctx.type+"!", ctx.lineno)
        }
    }

    input = (data, source="<string>", debug=false) => {
        this.lexdata = data;
        this.source = source;
        this.debug = debug;
        this.tokenizr.lineno = 0;
        this.tokenizr.e3lm_lexer = this;
        this.tokenizr.input(this.lexdata);
        this.tokenizr.debug(false);
        this.token_stream = this.make_token_stream();
        this.current_token = null;
        this.compute_input(data);
    }

    compute_input = (text, append="\n") => {
        if (this.computed == null) {
            this.computed = Object({});
        }
        for (const [key,val] of Object.entries(this.compute_pattern_inds)) {
            if (!(key in this.computed)) {
                this.computed[key] = [];
            }
        };

        text += "\n"; // Extend computed with a new line.

        // Compute matches
        var _append, _appendKey, _appendGroups, _appendNones;
        var matches = text.matchAll(this.compute_pattern);
        var marray = [...matches];
        var count = 0;
        for (var m=0; m < marray.length; m++) {
            var match = marray[m];
            for (var key of Object.keys(this.compute_pattern_inds)) {
                _append = false;
                _appendKey = key;
                _appendGroups = this.compute_pattern_inds[key];
                _appendNones = false;
                switch (_appendKey) {
                    case "comment": {_appendNones = true; break;}
                    case "newline": {_append = {"text": "!null", "newline": "\n"}; break;}
                    case "indent": {_append = {"indent": "spacelen()"}; break;}
                };
                for (var groupNum = 0; groupNum < match.length; groupNum++) {
                    // groupNum = groupNum + 1;
                    var group = match[groupNum];
                    if (_appendGroups.includes(groupNum)) {
                        if (_append || _appendNones || (!(_appendNones) && group != null)) {
                            if (_append) {
                                for (var ap of Object.keys(_append)){
                                    var apval = _append[ap];
                                    if (apval == "!null") {
                                        if (group != undefined) {
                                            this.computed[ap].push(group);
                                        }
                                    } else if (apval == "spacelen()") {
                                        if (group != undefined) {
                                            group = group.replace("\t", "    "); // Tabs to Spaces: 4 Spaces
                                            this.computed[ap].push(group.length);
                                        } else {
                                        }
                                    } else {
                                        this.computed[ap].push(apval);
                                    }
                                }
                            } else {
                                this.computed[_appendKey].push(group);
                            }
                        }
                    };
                }
            }
            count += 1;
        };

        var offsets = [0];
        for (var m=0; m < marray.length; m++) {
            var match = marray[m];
            offsets.push(match.index + match[0].length + 1);
        }
        this.line_offsets = offsets;
    }

    make_token_stream = () => {
        var me = this;
        var gen = function* (me) {
            var t = me.tokenizr.token();
            t = filter_strings(t);
            yield t
        };
        return gen;
    }

    filter_strings = function* (tokgen) {
        var tok = tokgen.next();
        if (tok.type.startsWith("STRING_START_")) {
            yield tok;
        }
        start_tok = tok;
        string_toks = [];
        var fin = false;
        tok = tokgen.next();
        while (tok.type != "STRING_END") {
            if (tok.type.startsWith("STRING_CONTINUE")) {
                string_toks.append(tok);
            } else {
                fin = true;
            }
            tok = tokgen.next();
        }
        if (!fin) {
            this.raise_error(this.tokenizr, type="SyntaxError", message="EOF while scanning string");
        }

        if (start_tok.type.includes("SINGLE")) {
            start_tok.lineno = tok.lineno;
        }

        start_tok.quotes = start_tok.type.slice(13);
        start_tok.type = "STRING";
        start_tok.value = this.convert_string(start_tok, string_toks);
        yield start_tok;
    }

    convert_string = (start_tok, string_toks) => {
        var i = 0;
        string_toks.forEach(tok => {
            if (tok.type == "STRING_CONTINUE_NEWLINE") {
                if (i+1 < string_toks.length) {
                    string_toks[i+1].value = string_toks[i+1].value.replace(/^[ \t]+/,"");
                }
                delete string_toks[i];
            }
        })
        var s = (string_toks.map((t) => {t.value})).join("");
        var quote_type = start_tok.value.toLowerCase();
        if (quote_type == "") {
            return s;
        }
        if (quote_type == "u") {
            s = String.fromCharCode(parseInt(s,16));
            return s;
        }
        throw 'Unknown string quote type: "' + quote_type + '".';
    }

    post_token = function* (tokgen) {
        var tok = tokgen.next();
        console.log("Filtering post_token of " + tok.type);
        if (!tok) {
            if (this.debug) {
                this.print_method("NO TOK!", "WARNING");
            }
            return;
        }
        if (tok.type == "NEWLINE") {
            this.tokenizr.lineno += 1;
        }

        if (this.last_token) {
            this.check_tokens.forEach((check) => {
                if (this.last_token.type.endsWith(check["tokens"][0])) {
                    if (check["tokens"][1].includes(tok.type)) {
                        this.raise_error(this.tokenizr, type="SyntaxError", message=check["message"]);
                    }
                }
            });
        }

        if (!(["WS", "NEWLINE",].includes(tok.type))) {
            this.last_token = tok;
        }
        if (["ATTR",].includes(tok.type)) {
            this.stack.follow_indent(tok);
        }

        var inds = this.computed["indent"][tok.lineno];
        if (this.debug) {
            // NOTE: COPY FROM LEXER.PY:906
        }

        if (!(["WS", "NEWLINE",].includes(tok.type))) {
            yield tok;
        } else {
        }
    }

    token = function* () {
        this.p_one = this.current_token;
        this.current_token = this.token_stream();
        if (this.current_token.done) {
            yield null;
        }
        yield this.current_token;
        /*  no more tokens  */
        return null;
    }

    tokens = () => {
        const result = [];
        let token;
        while ((token = this.token()) !== null)
            result.push(token);
        return result;
    };

    lex = (data, source="<string>", debug=false, token_map=true) => {
        this.input(data, source, debug=debug);
        if (token_map) {
            var _tokens = [];
            var toks = this.tokens();
            toks.forEach((token) => {
                _tokens.push(token)
            });
            return _tokens;
        } else {
            return this.tokenizr.tokens;
        }
    }
};

module.exports = E3lmLexer;