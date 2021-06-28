var chalk = require('chalk');

var COLORS = new chalk.Instance({level: 2});

COLORS["A"] = function (x) {return ("\x1b[38;5;164m" + x + "\x1b[0m");}
COLORS["B"] = function (x) {return ("\x1b[38;5;173m" + x + "\x1b[0m");}
COLORS["C"] = function (x) {return ("\x1b[38;5;177m" + x + "\x1b[0m");}
COLORS["D"] = function (x) {return ("\x1b[38;5;225m" + x + "\x1b[0m");}
COLORS["LOG"] = function (x) {return ("\x1b[38;5;164m" + x + "\x1b[0m");}
COLORS["LOG_MSG"] = function (x) {return ("\x1b[38;5;245m" + x + "\x1b[0m");}
COLORS["ERROR"] = function (x) {return ("\x1b[91m" + x + "\x1b[0m");}
COLORS["GRAY"] = function (x) {return ("\x1b[38;5;245m" + x + "\x1b[0m");}

module.exports = {
    COLORS: COLORS,
};