// myparser.js
var fs = require("fs");
const colors = require('colors');
var E3lmLexer = require('./lexer');

let e3lmfile = fs.readFileSync(process.argv[2], "utf-8");
var lexer = new E3lmLexer;

var tokens_array = lexer.lex(e3lmfile, source=process.argv[2], debug=true, token_map=true);


//tokens_array.forEach((token) => {
    //if (!(["WS","NEWLINE",].includes(token.type))) {
//        console.log(token.toString())
    //}
//});
