exports.execute = async (args) => {
    const dotenv = require('dotenv');
    const vscode = args.require('vscode');
    const cp = require("child_process");
    
    var file = vscode.window.activeTextEditor.document.fileName;

    dotenv.config({path: __dirname + '\\..\\.env'});
    const py = process.env.WORKSPACE + '\\' + process.env.VENV_NAME + '\\Scripts\\python'

    cp.exec(`"${py}" -m autopep8 --in-place "${file}"`, (err,stdout,stderr)=> {
        if (err) {
            vscode.window.showErrorMessage(`Autopep8: ${err}`);
        } else {
            file = file.split(/[\\/]/).pop(); // Basename
            vscode.window.showInformationMessage(
                `Autopep8 on "${file}" has been done.`
            );
        };
    });
}