// lexer.js

var fs = require("fs");
var path = require("path");
const langdata = require("./data");
const printers = require("./printers");

const COLORS = printers.COLORS;

// var Lexer = require('flex-js');
var Tokenizr = require('tokenizr');
const { default: Complex } = require("complex.js");
const tokens = langdata.tokens;
const regexes = langdata.regexes;


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
            stack["_indent_gt"] = this.lexer.computed["indent"][t.line - 1];
        }

        this.store.push(stack);
        this.id = this.store.length - 1;

        if (lexstate != null) {
            this.lexer.tokenizr.push(lexstate);
        }

        return this.id;
    }

    pop(poplex=false) {
        if (poplex) {
            this.lexer.tokenizr.pop();
        }
        var stack = this.store.pop();
        this.id -= 1;

        return stack;
    }

    follow_indent(t, val=null) {
        var lineno = t.line;
        var indents = this.lexer.computed["indent"][lineno];
        if (this.get("_indent_gt", undefined) != undefined) {
            var req_indents = this.get("_indent_gt")
            this.update("_indent", req_indents);
            indents = this.get("_indent");
            delete this.store[this.id]["_indent_gt"];
        } else {
            req_indents = this.get("_indent");
        }

        if (val) {
            this.update('_indent', val);
        }

        if (req_indents != indents) {
            var type, details;
            this.lexer.raise_error(t, "LexError", "Expected " + String(req_indents) + " indents, got " + String(indents) + ".",
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

    _newline_pattern = /\n/;
    
    debug = true
    print = (x, col="magenta", ...args) => {
        if (args.length == 0) {args = false;}
        if (this.debug) {
            if (col && typeof col != "string") {
                console.log(COLORS["LOG"]("LOG"), COLORS["LOG_MSG"](x), col, args ? COLORS["LOG_MSG"](...args) : "");
            } else {
                console.log(COLORS["LOG"]("LOG"), COLORS[col](x), args ? COLORS["LOG_MSG"](...args) : "");
            }
        }
    };
    default_state = 'INITIAL';
    
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
    re_class_def = new RegExp('(' + this.class_name_char + "*)([ \t]*(" +
        this.identifier_char + "*))?", 'y');
    
    re_attr = new RegExp('(' + this.identifier_char + '*' + ")(\\s*\=\\s*)", 'y')

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
        this.filter_strings.prototype.return = undefined;
        this.post_token.prototype.return = undefined;
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
        
        this.tokenizr.rule(this.default_state, this._newline_pattern, (ctx, match) => {
            ctx.accept('NEWLINE');
        }, 'rule_NEWLINE');
        
        this.tokenizr.rule(this.default_state, this.re_class_def, (ctx, match) => {
            if (match[1].toLowerCase() == "import") {
                ctx.ignore()
            } else {
                ctx.push('BLOCK');
                ctx.accept('CLASS', match[1]);
                // console.log(match[0]);
                if (match[3]) { ctx.accept('NAME', match[3]); }
            }
        }, 'rule_CLASS');
        
        // Unnecessary tokenization
        /*this.tokenizr.rule(this.default_state, this.re_identifier, (ctx, match) => {
            var type = 'ID';
            if (match[0].toLowerCase() in this.reserved) {type = this.reserved[match[0].toLowerCase()];}
            ctx.accept(type);
        }, 'rule_ID');*/
        
        // State: BLOCK
        
        this.tokenizr.rule('BLOCK', /[Ee][Nn][Dd](.*)/g, (ctx, match) => {
            ctx.accept('END');
            this.stack.pop(true);
            this.stack.indent_check = "lt"
        }, 'rule_BLOCK_END');

        this.tokenizr.rule('BLOCK', this.re_attr, (ctx, match) => {
            // Remove the equals part by getting the captured value only.
            var value = match[1];
            var type = 'ATTR';
            if (match[0].toLowerCase() in this.reserved) {
                type = this.reserved[match[0].toLowerCase()];
            }
            if (type != 'ATTR') {this.raise_error(ctx, 'SyntaxError', "Encountered reserved keyword");};
            ctx.push('EXPR');
            ctx.data('paren_level', 0);
            ctx.data('dict_level', 0);
            ctx.data('array_level', 0);
            var lineno = ctx.info().line;
            this.stack.update('_indent', this.computed["indent"][lineno]);
            ctx.accept(type, value);
        }, 'rule_BLOCK_ATTR');

        this.tokenizr.rule('BLOCK', /\-\-\-/g, (ctx, match) => {
            if (this.last_token.type == "BODY") {
                ctx.ignore();
                return
            }
            ctx.data('body_start', -1);
            ctx.data('body_start_lineno', -1);
            var nfo = ctx.info();
            var lineno = nfo.line;
            ctx.data('body_indent', this.computed["indent"][lineno + 1]);
            var t = {
                type: "BODYOPEN",
                value: "",
                pos: nfo.pos,
                line: nfo.line,
                len: nfo.len,
                col: nfo.col,
            };
            //ctx.accept(t.type, t);
            ctx.ignore();
            this.stack.push(t, {}, "BODY");

        }, 'rule_BLOCK_BODYOPEN');

        this.tokenizr.rule('BLOCK', /[ \t]/g, (ctx, match) => {
            ctx.accept('WS');
        }, 'rule_BLOCK_WS');
        
        this.tokenizr.rule('BLOCK', this.re_class_def, (ctx, match) => {
            ctx.push("BLOCK");
            ctx.accept('CLASS', match[1]);
            if (match[3]) { ctx.accept('NAME', match[3]); }
        }, 'rule_BLOCK_CLASS');

        /* this.tokenizr.rule('BLOCK', this.re_identifier, (ctx, match) => {
            var nfo = ctx.info();
            var t = {
                type: "NAME",
                value: match[0],
                pos: nfo.pos,
                line: nfo.line,
                len: nfo.len,
                col: nfo.col,
            };
            this.stack.push(t, {});
            this.stack.indent_check = "gt"
            ctx.accept(t.type, t.value);
        }, 'rule_BLOCK_NAME'); */

        this.tokenizr.rule('BLOCK', this._newline_pattern, (ctx, match) => {
            if (this.last_token.type == "CLASS") {
                this.stack.push(this.last_token, {});
                this.stack.indent_check = "gt"
            } else if (this.last_token.type == "NAME") {
                ctx.accept("NEWLINE");
                return
            }
            ctx.accept('NEWLINE');
        }, 'rule_BLOCK_NEWLINE');

        // State: EXPR

        this.tokenizr.rule('EXPR', /\\\n/g, (ctx, match) => {
            this.tokenizr._line += 1;
        }, 'rule_EXPR_escape'); // TODO: TEST

        this.tokenizr.rule('EXPR', /\\(.|\n)/g, (ctx, match) => {
            var type;
            if (match[0] == "\\\n") {
                type = "STRING_CONTINUE_NEWLINE";
            } else {
                type = "STRING_CONTINUE";
            }
            this.progress(match[0].split("\n").length - 1); // TODO: TEST
            nfo = ctx.info();
            ctx.accept(type)
        }, 'rule_SQ1_SQ2_TQ1_TQ2_escapes');
        //#endregion

        //#region Stings

        //#region TRIPLEQ1
        this.tokenizr.rule('EXPR', /[bB]?'''/g, (ctx, match) => {
            ctx.push('TRIPLEQ1');
            var type = "STRING_START_TRIPLEQ1";
            if (match[0].includes("r") || match[0].includes("R")) {
                ctx.data("string_raw", true);
            } else {
                ctx.data("string_raw", false);
            }
            var value = match[0].split("'", 1)[0]
            ctx.accept(type, value);
        }, 'rule_EXPR_start_str_TQ1');

        // State: TRIPLEQ1

        this.tokenizr.rule('TRIPLEQ1', /[^']+/g, (ctx, match) => {
            //this.tokenizr._line += match[0].split("\n").length - 1;
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
            ctx.push('TRIPLEQ2');
            var type = "STRING_START_TRIPLEQ2";
            if (match[0].includes("r") || match[0].includes("R")) {
                ctx.data("string_raw", true);
            } else {
                ctx.data("string_raw", false);
            }
            var value = match[0].split('"', 1)[0]
            ctx.accept(type, value);
        }, 'rule_EXPR_start_str_TQ2');

        // State: TRIPLEQ2

        this.tokenizr.rule('TRIPLEQ2', /[^"]+/g, (ctx, match) => {
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
            // this.tokenizr.reset();
            var type = "STRING_START_SINGLEQ1"
            if (match[0].includes("r") || match[0].includes("R")) {
                ctx.data("string_raw", true);
            } else {
                ctx.data("string_raw", false);
            }
            var value = match[0].split('"', 1)[0]
            ctx.accept(type, value);
        }, 'rule_EXPR_start_str_SQ1');

        // State: SINGLEQ1

        this.tokenizr.rule('SINGLEQ1', /[^"]+/g, (ctx, match) => {
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
                ctx.data("string_raw", true);
            } else {
                ctx.data("string_raw", false);
            }
            var value = match[0].split("'", 1)[0]
            ctx.accept(type, value);
        }, 'rule_EXPR_start_str_SQ2');

        // State: SINGLEQ2

        this.tokenizr.rule('SINGLEQ2', /[^']+/g, (ctx, match) => {
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

        this.tokenizr.rule('EXPR', this._newline_pattern, (ctx, match) => {
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
        this.tokenizr.rule('BODY', this._newline_pattern, (ctx, match) => {
            var body_start = ctx.data('body_start');
            var body_start_lineno = ctx.data('body_start_lineno');
            var body_indent = ctx.data('body_indent');
            var body_tokens = ctx.data('body_tokens');
            var nfo = ctx.info();
            if (body_start == -1) {
                body_start = nfo.pos;
                body_start_lineno = nfo.line;
                body_tokens = this.computed['text'][body_start_lineno - 1];
                if (body_tokens != null) {body_tokens = body_tokens.slice(3); }
                ctx.data('body_start', body_start);
                ctx.data('body_start_lineno', body_start_lineno);
                ctx.data('body_tokens', body_tokens);
            }
            var starting_indent = this.computed['indent'][body_start_lineno - 1];
            var ahead_indent = this.computed['indent'][nfo.line + 0];
            var prev_text = this.computed['text'][nfo.line - 2];
            var curr_text = this.computed['text'][nfo.line - 1];
            var ahead_text = this.computed['text'][nfo.line + 0];
            ahead_text = ahead_text ? ahead_text : "";
            var close = false;
            var add = "";

            if (body_indent == -1) {
                close = false;
            }

            var tpos;
            if (!close && prev_text.startsWith("---")) {
                if (ahead_text.startsWith("---")) {
                    close = true;
                    tpos = nfo.pos;
                    add = "0";
                }
            } else if (!close && (ahead_text.startsWith("---"))) {
                close = true;
                // Get last character for newline.
                tpos = nfo.pos;
            }
            
            if (!close) {
                if (ahead_indent < starting_indent) {
                    if (ahead_text.startsWith("---") != true) {
                        close = true;
                        if (curr_text != "\n") {
                            add = " ".repeat(this.computed["indent"][nfo.line]) + this.computed["text"][nfo.line];
                            tpos = nfo.pos;
                        } else {
                            add = " ".repeat(this.computed["indent"][nfo.line-1]) + this.computed["text"][nfo.line-1];
                            tpos = nfo.pos;
                        }
                    }
                }
            }
            
            if (close) {
                var _skip = add.length; if (_skip == 0) _skip = 1;
                this.progress(_skip);
                nfo = ctx.info();
                var bbody = this.lexdata.slice(body_start, nfo.pos+1);
                var bvalue = this.bodify_indents(bbody, body_indent)
                var type = "BODY";
                var btokens = body_tokens.split(",");
                ctx.accept(type, bvalue);
                nfo = ctx.info();
                this.tokenizr._pending[0].tokens = btokens;
                this.tokenizr._pending[0].endline = this.tokenizr._pending[0].line;
                this.tokenizr._pending[0].line = body_start_lineno;
                ctx.data("body_tokens", null);
                ctx.data("body_start", null);
                ctx.data("body_start_lineno", null);
                this.stack.pop(true);
            } else {
                // NEWLINE...
                ctx.ignore();
                this.progress(this.computed["lengthx"][nfo.line]);
            }

        }, 'rule_BODY_NEWLINE');

        this.tokenizr.rule('BODY', /.+/g, (ctx,match) => {
            ctx.ignore();
        }, 'rule_BODY_text');

        //#endregion

        // this.tokenizr.rule('EXPR', regexes.Imagnumber, (ctx, match) => {
        // }, 'rule_EXPR_escape'); // TODO: ENABLE

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

    raise_error = (ctx, type="LexError", message="", details={}) => {
        var e = Error();
        e.type = type;
        e.message = message;
        e.source = this.source;
        e.info = ctx.info() ;
        if (details.length > 0) {e.extra = details;}
        throw e;
    }

    progress = (nchar) => {
        this.tokenizr._progress(this.tokenizr._pos, this.tokenizr._pos + nchar);
        this.tokenizr._pos += nchar;
    }

    input = (data, source="<string>", debug=false) => {
        if (source != "<string>") {
            this.source_path = path.resolve(path.dirname(source));
        } else {
            this.source_path = process.cwd();
        }
        data = data.replace(/\r\n/g, "\n");
        data = this.resolve_imports(data);
        this.lexdata = data;
        this.source = source;
        this.debug = debug;
        this.tokenizr.reset();
        // this.tokenizr.e3lm_lexer = this;
        this.tokenizr.input(this.lexdata);
        this.tokenizr.debug(false);
        this.tokenizr.state(this.default_state);
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
        
        this.computed["lengthx"] = [];
        for (var m=0; m < this.computed["text"].length; m++) {
            this.computed["lengthx"].push(
                this.computed["text"][m].endsWith("\n") ? this.computed["text"][m].length : this.computed["text"][m].length+1
                + this.computed["indent"][m]
                + (this.computed["comment"][m] ? this.computed["comment"][m].length : 0)
            );
        }
    }

    resolve_imports = function (text) {
        var regex = regexes["IMPORT"];

        let m;
        while ((m = regex.exec(text)) !== null) {
            var ff = m[3]; // Filename
            var indents = m[1].length; // Indents
            var comment = ""; // Comment
            if (m.length > 3) {
                var comment = m[4];
            }
            if (!ff.endsWith(".3lm")) {
                ff = ff + ".3lm"
            }
            ff = path.resolve(this.source_path, ff);
            var contents = fs.readFileSync(ff, "utf-8");

            contents = contents.replace(/\r\n/g, "\n");
            var contentsA = contents.split("\n");
            contentsA.forEach( (ele,ind) => {
                contentsA[ind] = " ".repeat(indents) + ele;
            });
            contents = contentsA.join("\n");
            text = text.replace(m[0], contents);
            regex.lastIndex = 0;
        }
        return text;
    }

    filter_strings = function* (toks) {
        var tok;
        for (tok of toks) {
            if (!(tok.type.startsWith("STRING_START_"))) {
                yield tok;
                continue;
            }
            var start_tok = tok;
            var string_toks = [];
            var fin = false;
            while (true) {
                tok = toks.get_next();
                if (tok.type == "STRING_END") {
                    fin = true;
                    break;
                } else {
                    if (tok.type.startsWith("STRING_CONTINUE")) {
                        string_toks.push(tok);
                    } else {
                        fin = true;
                    }
                }
                if (tok == undefined) {break;}
            }
            if (!fin) {
                this.raise_error(this.tokenizr, type="SyntaxError", message="EOF while scanning string");
            }
            
            if (start_tok.type.includes("SINGLE")) {
                start_tok.line = tok.line;
            }
            
            start_tok.quotes = start_tok.type.slice(13);
            start_tok.quote = start_tok.text;
            start_tok.type = "STRING";
            start_tok.value = this.convert_string(start_tok, string_toks);
            start_tok.value_quoted = start_tok.quote + start_tok.value + start_tok.quote;
            start_tok.text = start_tok.value
            yield start_tok;
        }
    };

    convert_string = (start_tok, string_toks) => {
        var i = 0;
        for (i=0; i<string_toks.length; i++) {
            var tok = string_toks[i];
            if (tok.type == "STRING_CONTINUE_NEWLINE") {
                if (i+1 < string_toks.length) {
                    string_toks[i+1].value = string_toks[i+1].value.replace(/^[ \t]+/,"");
                }
                delete string_toks[i];
            }
        };
        var s = (string_toks.map(t => t.value)).join("");
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

    post_token = function* (toks) {
        var tok;
        for (tok of toks) {
            if (!tok) {
                if (this.debug) {
                    this.print("No tokens found!", "ERROR"); // STRING
                }
                yield null;
                break;
            }
            if (tok.type == "NEWLINE") {
                // Here the tokenizr doesn't require a line increment.
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

            if (!(["WS", "NEWLINE",].includes(tok.type))) {
                yield tok;
                continue;
            } else {
                continue;
            }
        }
    };

    make_token_stream = function () {
        var me = this;
        const myIterable = {};
        myIterable[Symbol.iterator] = function* () {
            var xx = me.tokenizr.token();
            while (xx != null) {
                yield xx
                var xx = me.tokenizr.token();
            }
        };
        myIterable["get_next"] = function() {
            var xx = me.tokenizr.token();
            return xx;
        }
        var x = this.post_token(this.filter_strings(myIterable));
        return x;
    }

    token = function* () {
        this.p_one = this.current_token;
        var ts, ct;
        ct = this.token_stream.next();
        while (ct != null && (ct.done !== true)) {
            var t = ct.value;
            this.current_token = t;
            ct = this.token_stream.next();
            yield t;
        }
        /*  no more tokens  */
        yield null;
    };

    print_token = (t, offset=-1) => {
        var val = COLORS["D"](String(t.type != "BODY" ? (t.value_quoted ? t.value_quoted : t.value) : (t.value)) + "");
        val = val.replace(/\n/g, "\\n")
        //val = val.substr(0, 71)!=val ? val.substr(0, 71)+"..." : val;

        this.print(" ".repeat(1+this.computed["indent"][t.line-1]
            + (offset == t.line ? (t.type != "NAME" ? 1 : 0) : 0)) + COLORS["B"]("T ") + COLORS["C"](String(t.type)
            + ((t.value) ? (COLORS["GRAY"](" = ") + val) : " = null"))
            // + "]#red["+ String(t.type == "BODY" ? String(t.endline) : "") + "]"
        );
    }

    get_tokens = () => {
        var result = [];
        var token;
        var gen = this.token();
        // this.print("get_tokens:");
        var cline = 0;
        while ((token = gen.next()).done !== true)
            {
            var t = token.value;
            if (t && t.hasOwnProperty("type")) {
                result.push(t);
                if (!(["NEWLINE", "WS", "EOF"].includes(t.type))) {
                    this.print_token(t, cline)
                    cline = t.line;
                    }
                }
            }
        return result;
    };

    lex = (data, source="<string>", debug=false, token_map=true) => {
        this.input(data, source, debug=debug);
        if (token_map) {
            var _tokens = [];
            var toks = this.get_tokens();            
            toks.forEach((token) => {
                _tokens.push(token)
            });
            return _tokens;
        } else {
            return this.get_tokens;
        }
    }

    bodify_indents = (string, indents) => {
//        console.log(string, indents);
        if (string) {
            //console.log(string);
            string = string.split("\n");
            var s, j;
            var new_strings = []
            for (s of string) {
                var ss = s.slice(0, indents+1);
                j = 0;
                for (const [i,ch] of Object.entries(ss)) {
                    if (!([" ", " ", "\t"].includes(ch))) { j=i; break; } else {j+=1; }
                }
                new_strings.push(s.slice(j));
            }
            return new_strings.join("\n");
        }
        return string;
    }
};

module.exports = E3lmLexer;