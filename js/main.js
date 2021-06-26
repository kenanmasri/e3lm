// main.js


const jison = require("jison")
const fs = require("fs");
const env = require("dotenv");
const dotenv = require('dotenv');
dotenv.config({path: __dirname + '\\..\\.env'});

const parserOutFile = __dirname + '\\..\\' + 'src\\e3lm\\lang\\parser.out';

readParser = (file) => {
    fs.readFile(file, function (err, data) {
        if (err) return console.error(err);
        console.log(data.toString());
    });
}

readParser(parserOutFile);