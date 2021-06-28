// myparser.js
var fs = require("fs");
var E3lmLexer = require('./lexer');

let e3lmfile = fs.readFileSync(process.argv[2], "utf-8");
var lexer = new E3lmLexer;

token_map = true;
var tokens_array = lexer.lex(e3lmfile, source=process.argv[2], debug=true, token_map=token_map);

if (!token_map) {
    for (token of tokens_array()) {
        console.log("t", token);
    };
}
