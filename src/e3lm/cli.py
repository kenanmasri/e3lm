# -*- coding: utf-8 -*-
"""The e3lm CLI tool (3lm language) for managing 3lm projects and files.

This tool is designed mainly to enable interpretation of 3lm files and
upgrading the interpreter and its plugins.
"""
__version__ = "0.1.9"

__doc2__ = """additional arguments:
    Nothing for now.
"""

__doc3__ = """additional arguments:
  --plugin-list         view available plugins, use the following command:
  --plugin-install plugin
                        install a specific plugin
  --plugin-update plugin
                        update a specific plugin
  --plugin-uninstall plugin
                        uninstall a specific plugin
  --clear-cache         clear the temporary files cache
  --lang-update         check for language updates
"""

import argparse
import io
import itertools
import json
import os
import signal
import subprocess
import sys
from shlex import quote
from time import perf_counter, sleep

from graphviz import Source as GraphvizSource

from e3lm.contrib.dot import DotPlugin as Dot
from e3lm.contrib.json import JsonPlugin as Json
from e3lm.demos.data import getcode as gettestcode
from e3lm.helpers import printers
from e3lm.helpers.printers import COLORS
from e3lm.lang.ast import basic_dt
from e3lm.lang.interpreters import E3lmInterpreter, E3lmPlugin
from e3lm.utils.lang import get_plugin, interpret, lex, parse

# Variables

CLI_PLUGINS = [
    "view",
    "lex",
    "parse",
]  # Plugins that are not E3lmPlugin


def windows_enable_ANSI(std_id):
    """Enable Windows 10 cmd.exe ANSI VT Virtual Terminal Processing."""
    from ctypes import POINTER, WINFUNCTYPE, byref, windll
    from ctypes.wintypes import BOOL, DWORD, HANDLE

    GetStdHandle = WINFUNCTYPE(
        HANDLE,
        DWORD)(('GetStdHandle', windll.kernel32))

    GetFileType = WINFUNCTYPE(
        DWORD,
        HANDLE)(('GetFileType', windll.kernel32))

    GetConsoleMode = WINFUNCTYPE(
        BOOL,
        HANDLE,
        POINTER(DWORD))(('GetConsoleMode', windll.kernel32))

    SetConsoleMode = WINFUNCTYPE(
        BOOL,
        HANDLE,
        DWORD)(('SetConsoleMode', windll.kernel32))

    if std_id == 1:       # stdout
        h = GetStdHandle(-11)
    elif std_id == 2:     # stderr
        h = GetStdHandle(-12)
    else:
        return False

    if h is None or h == HANDLE(-1):
        return False

    FILE_TYPE_CHAR = 0x0002
    if (GetFileType(h) & 3) != FILE_TYPE_CHAR:
        return False

    mode = DWORD()
    if not GetConsoleMode(h, byref(mode)):
        return False

    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    if (mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING) == 0:
        SetConsoleMode(h, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    return True


if sys.platform == "win32":
    windows_enable_ANSI(0)  # Windows 10 VirtualTerminal Ansi on Stdout
    windows_enable_ANSI(1)  # Windows 10 VirtualTerminal Ansi on Stderr

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# E3lm CLI


def arg_required_length(nmin, nmax):
    class RequiredLength(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            if not nmin <= len(values) <= nmax:
                msg = 'argument "{f}" requires between {nmin} and {nmax} arguments'.format(
                    f=self.dest, nmin=nmin, nmax=nmax)
                raise argparse.ArgumentTypeError(msg)
            setattr(args, self.dest, values)
    return RequiredLength


def demo_file(f):
    if f.startswith("code"):
        n = int(f[4:])
        prefix = "code"
    elif f.startswith("errorcode"):
        n = int(f[9:])
        prefix = "errorcode"
    else:
        n = int(f)
    return gettestcode(n, prefix)
    # return "<<..demo file " + str(f) + "..>>"


def demo_exists(f):
    return demo_file(f) != None


def CLI(input_file="-", kwargs={}):
    """The actual CLI."""
    if kwargs:
        quiet = kwargs["quiet"]
        verbose = kwargs["verbose"]
        verbose_lvl = kwargs["verbose_lvl"]
        demos = kwargs["demos"]
        plugins = kwargs["plugins"]
        nocolors = kwargs["nocolors"]
        noglyph = kwargs["noglyph"]
        formatstyle = kwargs["formatstyle"]
        benchmarking = kwargs["benchmarking"]
        benchmarking_mods = kwargs["benchmarking_mods"]
        colors = kwargs["colors"]
        e3lm_parser = kwargs["e3lm_parser"]

    shown_msgs = {}
    runstack = {}
    runtime = {}
    special_positionals = ("?", "help",  # Help alternatives.
                           "-", ".",  # No or all file(s)
                           )

    tmpdir = os.getenv("E3LM_TEMP_DIRECTORY", "tmp")
    if not os.path.exists(tmpdir):
        os.mkdir(tmpdir)

    # Check for special positional argument values in place of "file"
    if input_file in special_positionals:
        if input_file in ["?", "help"]:
            sys.exit(e3lm_parser.print_help(None))
        elif input_file in ["-", "."]:
            if input_file == "-":
                input_file = None
            else:
                runstack.update({os.path.basename(f): os.path.abspath(f)
                                for f in os.listdir(os.getcwd()) if f.endswith(".3lm")})
                input_file = None

    # Check if file exists... otherwise use demos.
    if input_file != None:
        if (os.path.exists(input_file) or os.path.exists(input_file + ".3lm")) \
                and (os.path.isfile(input_file) or os.path.isfile(input_file + ".3lm")):
            if not input_file.endswith(".3lm"):
                input_file = input_file + ".3lm"
            runstack.update({input_file: input_file})
        else:
            if not input_file.endswith(".3lm"):
                input_file = input_file + ".3lm"
            if not os.path.isfile(input_file):
                # if not quiet:
                print(colors["E"] + 'Error: ' + input_file +
                      ' does not exist.' + colors["R"], file=sys.stderr)
            # elif not quiet:
            else:
                print(colors["E"] + 'Error: ' + input_file +
                      ' is a directory.' + colors["R"], file=sys.stderr)
            sys.exit(1)

    # Check if demos are specified
    if len(demos) > 0:
        runstack.update({d: demo_file(d) for d in demos if demo_exists(d)})

    # Load up each stack content (file or directly)
    for key, val in runstack.items():
        if os.path.isfile(val) and os.path.exists(val):
            try:
                f = open(val, encoding='utf-8')
                d = "".join(f.readlines())
                if benchmarking_mods["enabled"]:
                    d = (d + "\n") * int(benchmarking_mods["lengthofcode"])
                    runstack[key] = d
                runstack[key] = d
            finally:
                f.close()
        else:
            d = val
            if benchmarking_mods["enabled"]:
                d = (d + "\n") * int(benchmarking_mods["lengthofcode"])
            runstack[key] = d

    # Print headers for each runtime
    for i, run in runstack.items():
        if formatstyle == "DEFAULT":
            printers.cprint(colors["3"] + "--" + colors["1"] + "== " + colors["4"] +
                            i + colors["1"] + " ==" + colors["3"] + "--" + colors["R"], color="" if nocolors else "SUCCESS")
        elif formatstyle == "MIN":
            pass
        elif formatstyle == "COMPATIBLE":
            print("Runtime.begin", i)

        run_plugins = [get_plugin(p) for p in plugins if p not in CLI_PLUGINS and
                       type(get_plugin(p)) not in basic_dt]

        if "lex" in plugins:
            run_program = lex(run, i, debug=verbose_lvl >= 2,
                              enable_colors=nocolors == False, tracking=verbose_lvl >= 2)
            return True

        if "parse" in plugins:
            run_program = parse(run, i, parser_kwargs={
                "tracking": verbose_lvl >= 2,
                "enable_colors": nocolors == False,
                "debug": verbose_lvl >= 2,
            }, debug=verbose_lvl >= 3)
            if verbose_lvl >= 2:
                if not benchmarking_mods["enabled"]:
                    if formatstyle == "COMPATIBLE":
                        print("Program.begin", i)
                    printers.nprint(run_program, max_level=0, pallete=None if nocolors else COLORS,
                                    noglyph=noglyph, program_name=i, evaluate=False)
                    if formatstyle == "COMPATIBLE":
                        print("Program.end")

                else:
                    if "benchmarking_parse" not in shown_msgs.keys():
                        count = str(len(run.splitlines()))
                        shown_msgs["benchmarking_parse"] = True
                        if formatstyle == "DEFAULT":
                            print(colors["2"] + "       - " + colors["H"] +
                                  count + " line(s) of code Total." + colors["R"])
                        elif formatstyle == "COMPATIBLE":
                            print("Benchmark.info:", count)

        run_program = interpret(run, i,
                                plugins=run_plugins,
                                debug=verbose_lvl >= 3, enable_colors=nocolors == False,
                                parser_kwargs={
                                    "tracking": verbose_lvl >= 2,
                                    "enable_colors": True,
                                    "debug": verbose_lvl >= 3,
                                }
                                )
        if verbose_lvl >= 2:
            if not benchmarking_mods["enabled"]:
                if formatstyle == "COMPATIBLE":
                    print("Program.begin", i)
                printers.nprint(run_program, max_level=0, pallete=None if nocolors else COLORS,
                                noglyph=noglyph, program_name=i, evaluate=True)
                if formatstyle == "COMPATIBLE":
                    print("Program.end")
            else:
                if "benchmarking_parse" not in shown_msgs.keys():
                    count = str(len(run.splitlines()))
                    shown_msgs["benchmarking_parse"] = True
                    if formatstyle == "DEFAULT":
                        print(colors["2"] + "       - " + colors["H"] +
                              count + " line(s) of code Total." + colors["R"])
                    elif formatstyle == "COMPATIBLE":
                        print("Benchmark.info.loc_count", count)

                if "benchmarking_intr" not in shown_msgs.keys():
                    count = str(len(run_program.flat_blocks))
                    shown_msgs["benchmarking_intr"] = True
                    if formatstyle == "DEFAULT":
                        print(colors["2"] + "       - " + colors["H"] +
                              count + " blocks(s) Total." + colors["R"])
                    elif formatstyle == "COMPATIBLE":
                        print("Benchmark.info.block_count", count)

        if "benchmarking_parse" in shown_msgs.keys():
            del shown_msgs["benchmarking_parse"]
        if "benchmarking_intr" in shown_msgs.keys():
            del shown_msgs["benchmarking_intr"]

        if run_program == None:
            print("None")
        if "json" in plugins:
            if formatstyle == "COMPATIBLE":
                print("Plugin.json.begin")
            print(json.dumps(run_program.json, indent=4))
            if formatstyle == "COMPATIBLE":
                print("Plugin.json.end")

        if "view" in plugins:
            if run_program:
                if not hasattr(run_program, "dot_source"):
                    if formatstyle == "DEFAULT":
                        print(
                            colors["E"] + 'Error: Program does not have dot_source.' + colors["R"], file=sys.stderr)
                    elif formatstyle == "COMPATIBLE":
                        print("Plugin.view.error",
                              "Program does not have dot_source.")
                    exit(1)

                if formatstyle == "DEFAULT":
                    graph = GraphvizSource(
                        run_program.dot_source, filename=tmpdir + "/" + i + ".dot", format="png")
                    graph.view()
                elif formatstyle == "COMPATIBLE":
                    print("Plugin.dot.begin")
                    print(run_program.dot_source)
                    print("Plugin.dot.end")
            else:
                if formatstyle == "DEFAULT":
                    print("Nothing to view")
                elif formatstyle == "COMPATIBLE":
                    print("Plugin.view.info", "Nothing to view")

    sys.exit(0)


def caller(the_call, _type="subprocess", shell=True, ret=False, stdout=-1, stderr=-1):
    """Calls a shell command, or a program."""

    if _type == "os":
        proc = subprocess.Popen(the_call,
                                shell=shell,
                                stdout=stdout,
                                bufsize=-1,
                                stderr=stderr,
                                # preexec_fn=os.setsid
                                )
        if ret:
            return proc
        try:
            p = os._wrap_close(io.TextIOWrapper(proc.stdout), proc)
            return p.read()
        except KeyboardInterrupt:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            return False

    elif _type == "subprocess":
        p = subprocess.Popen(the_call, shell=shell,
                             stderr=stderr, stdout=stdout)
        return p


def BENCHMARK(input_file, kwargs={}):
    import math

    if kwargs:
        quiet = kwargs["quiet"]
        verbose = kwargs["verbose"]
        verbose_lvl = kwargs["verbose_lvl"]
        demos = kwargs["demos"]
        plugins = kwargs["plugins"]
        nocolors = kwargs["nocolors"]
        noglyph = kwargs["noglyph"]
        formatstyle = kwargs["formatstyle"]
        benchmarking = kwargs["benchmarking"]
        benchmarking_mods = kwargs["benchmarking_mods"]
        colors = kwargs["colors"]

    shown_msgs = {}
    py = "python"
    if formatstyle == "DEFAULT":
        printers.cprint(colors["2"] + "--" + colors["2"] + "== " + colors["2"] +
                        "Benchmarking..." + colors["2"] + " ==" + colors["2"] + "--" + colors["R"], color="" if nocolors else "SUCCESS")
    elif formatstyle == "COMPATIBLE":
        print("Benchmark.begin")

    sys_argv_ = sys.argv
    sys_argv_.pop(0)
    sys_argv_.append("--benchmark-mods")
    sys_argv_.append(
        "lengthofcode=" + str(benchmarking[1]) + "," +
        "iterations=" + str(benchmarking[0]) + ""
    )

    iterations = 0
    err_count = 0
    timelog = []

    while iterations < int(benchmarking[0]):
        # Open a subprocess for running the wanted command...
        try:
            # Remove the benchmark arguments and pass the rest to the caller.
            strings = sys_argv_
            for string in strings:
                if string == "-b" or string == "--benchmark":
                    pos = strings.index(string) + 1
                    if benchmarking[0] != 0:
                        if benchmarking[0] == strings[pos]:
                            strings.pop(pos)
                            pos -= 1
                    if benchmarking[1] != 0:
                        if benchmarking[1] == strings[pos + 1]:
                            strings.pop(pos + 1)
                            pos -= 1
                    strings.remove(string)
                    break

            p = caller([sys.executable, __file__] + strings, _type="subprocess", shell=False, ret=True)
            pout = os._wrap_close(io.TextIOWrapper(p.stdout), p)
            perr = os._wrap_close(io.TextIOWrapper(p.stderr), p)

            t_start = perf_counter()
            read_total_perr = ""
            read_total_pout = ""
            for c in itertools.cycle([
                '⡀', '⠄', '⠂', '⠁', '⠈', '⠐', '⠠', '⢀',
            ]):
                if "benchmark_first_iteration" not in shown_msgs.keys():
                    read_pout = pout.read()
                    read_perr = perr.read()
                    read_total_pout = read_total_pout + "\n" + read_pout
                    read_total_perr = read_total_perr + "\n" + read_perr
                    if read_pout != "":
                        if formatstyle == "DEFAULT":
                            print(colors["2"] + "       OUT: " +
                                  colors["R"] + read_pout)
                        elif formatstyle == "COMPATIBLE":
                            print("Benchmark.out", read_pout)
                    if read_perr != "":
                        if formatstyle == "DEFAULT":
                            print(colors["E"] + "       ERR: " +
                                  colors["R"] + read_perr)
                        elif formatstyle == "COMPATIBLE":
                            print("Benchmark.err", read_perr)
                        raise TimeoutError("An error occured, aborting..")
                if p.poll() != None:
                    shown_msgs["benchmark_first_iteration"] = True
                    break
                else:
                    if formatstyle == "DEFAULT":
                        sys.stdout.write('\r' + c + ' ' +
                                         "inst: " + str(iterations) + "  ")
                        sys.stdout.flush()
                    sleep(0.033)
            t_end = perf_counter()
        except KeyboardInterrupt:
            if formatstyle == "DEFAULT":
                print(colors["GREEN"] +
                      "\nUser cancelled (KeyboardInterrupt)" + colors["R"])
                printers.cprint(colors["2"] + "--" + colors["2"] + "== " + colors["2"] +
                                "Benchmarking done..." + colors["2"] + " ==" + colors["2"] + "--" + colors["R"] + "\n", color="" if nocolors else "SUCCESS")
            elif formatstyle == "COMPATIBLE":
                print("Benchmark.cancelled")
                print("Benchmark.end")

            exit(0)
        except TimeoutError as e:
            if formatstyle == "DEFAULT":
                print(colors["GREEN"] + "Timeout: " + str(e) + colors["R"])
                printers.cprint(colors["2"] + "--" + colors["2"] + "== " + colors["2"] +
                                "Benchmarking done..." + colors["2"] + " ==" + colors["2"] + "--" + colors["R"] + "\n", color="" if nocolors else "SUCCESS")
            elif formatstyle == "COMPATIBLE":
                print("Benchmark.timeout", str(e))
                print("Benchmark.end")
            exit(1)

        timelog.append({
            "iteration": iterations,
            "start": t_start,
            "end": t_end,
            "stdout": read_total_pout,
            "stderr": read_total_perr,
        })

        iterations += 1

    if formatstyle == "DEFAULT":
        sys.stdout.write('\r' + 'Total iterations: ' + str(iterations) + '\n')
    elif formatstyle == "COMPATIBLE":
        sys.stdout.write('Benchmark.info.total_iter ' + str(iterations) + '\n')
    sys.stdout.flush()

    if formatstyle == "DEFAULT":
        [print(str(t["iteration"]) + " => " + str(round((t["end"] - t["start"]) *
                                                        1000, 1000))[:6] + " ms") for t in timelog]
    elif formatstyle == "COMPATIBLE":
        [print("Benchmark.info.iter", str(t["iteration"]) + " " + str(round((t["end"] - t["start"]) *
                                                                            1000, 1000))[:6] + " ms") for t in timelog]

    durations = [t["end"] - t["start"] for t in timelog]
    if formatstyle == "DEFAULT":
        print(colors["1"] + "Max: " + colors["HEADER"] + str(round((max(durations)) *
                                                                   1000, 1000))[:6] + colors["1"] + " ms" + colors["R"])
        print(colors["1"] + "Min: " + colors["HEADER"] + str(round((min(durations)) *
                                                                   1000, 1000))[:6] + colors["1"] + " ms" + colors["R"])
        print(colors["1"] + "Avg: " + colors["HEADER"] + str(round((sum(durations) /
                                                                    iterations) * 1000, 1000))[:6] + colors["1"] + " ms" + colors["R"])
        printers.cprint(colors["2"] + "--" + colors["2"] + "== " + colors["2"] +
                        "Benchmarking done..." + colors["2"] + " ==" + colors["2"] + "--" + colors["R"] + "\n", color="" if nocolors else "SUCCESS")
    elif formatstyle == "COMPATIBLE":
        print("Benchmark.info.max", str(round((max(durations)) *
                                              1000, 1000))[:6])
        print("Benchmark.info.min", str(round((min(durations)) *
                                              1000, 1000))[:6])
        print("Benchmark.info.avg", str(round((sum(durations) /
                                               iterations) * 1000, 1000))[:6])
        print("Benchmark.end")

    exit(0)


def main():
    e3lm_parser = argparse.ArgumentParser(prog='e3lm',
                                          usage='%(prog)s [options] file',
                                          description=__doc__,
                                          formatter_class=argparse.RawTextHelpFormatter,
                                          epilog=__doc2__)

    e3lm_parser.add_argument('--version', action="version",
                             version="e3lm CLI v" + __version__ + " (3lm language)")

    e3lm_parser.add_argument('file',
                             nargs='?',
                             default='-',
                             help='path to the 3lm file (automatically detects extension) or - for nothing',
                             )

    e3lm_parser.add_argument('-q',
                             '--quiet',
                             action='store_true',
                             dest='quiet',
                             default=False,
                             help='run quietly without any output')

    e3lm_parser.add_argument('-nc',
                             '--no-color',
                             action='store_true',
                             dest="nocolors",
                             default=False,
                             help='set output to be without ANSI colors')

    e3lm_parser.add_argument('-ng',
                             '--no-glyph',
                             action='store_true',
                             dest="noglyph",
                             default=False,
                             help='use non-glyph character to avoid encoding issues')

    e3lm_parser.add_argument('-v',
                             '--verbose',
                             action='store',
                             metavar='NONE|ERROR|INFO|DEBUG',
                             dest='verbose',
                             type=str,
                             choices=["NONE", "ERROR", "INFO", "DEBUG"],
                             default="INFO",
                             help='filter output messages (default is INFO)')

    # e3lm_parser.add_argument('-i',
    #                          '--interactive',
    #                          action='store_true',
    #                          default=False,
    #                          help='execute with interactive mode')

    e3lm_parser.add_argument('-p',
                             '--plugin',
                             action='store',
                             metavar='plugin',
                             type=str,
                             default="",
                             nargs="+",
                             help='interpret using plugin(s). see below')

    e3lm_parser.add_argument('-d',
                             '--demo',
                             dest='demo',
                             metavar="code<n>",
                             action='store',
                             nargs='+',
                             type=str,
                             help='interpret demos in addition'
                             )

    e3lm_parser.add_argument('-b',
                             '--benchmark',
                             metavar='N',
                             dest='benchmarking',
                             default=False,
                             action=arg_required_length(0, 2),
                             nargs="*",
                             help="Benchmark N number of times [and N times length of code]",
                             )

    e3lm_parser.add_argument('-fs',
                             '--formatstyle',
                             action='store',
                             metavar='DEFAULT|MIN|COMPATIBLE',
                             dest='formatstyle',
                             type=str,
                             choices=["DEFAULT", "MIN", "COMPATIBLE"],
                             default="DEFAULT",
                             help='Formatting of the output messages',
                             )

    # For passing BENCHMARK to subprocess to modify length of codes.
    e3lm_parser.add_argument('--benchmark-mods',
                             dest='benchmarking_mods',
                             required=False, type=str,
                             help=argparse.SUPPRESS)

    args = e3lm_parser.parse_args()

    quiet = args.quiet
    if quiet:
        verbose = "NONE"
    verbose = args.verbose.upper()
    verbose_lvl = 1 if verbose == "ERROR" else 2 if verbose == "INFO" else 3 if verbose == "DEBUG" else 0
    input_file = args.file
    demos = args.demo or []
    plugins = args.plugin or []
    nocolors = args.nocolors
    noglyph = args.noglyph
    formatstyle = args.formatstyle

    colors = COLORS
    if nocolors:
        colors = {k: "" for k in COLORS.keys()}
    benchmarking = args.benchmarking
    benchmarking_mods = args.benchmarking_mods
    if benchmarking_mods == None:
        benchmarking_mods = {}
        benchmarking_mods["enabled"] = False
    else:
        benchmarking_mods = benchmarking_mods.split(",")
        benchmarking_mods = {b.split('=')[0]: b.split(
            '=')[1] for b in benchmarking_mods}
        benchmarking_mods["enabled"] = True

    kwargs = {
        "args": args,
        "quiet": quiet,
        "verbose": verbose,
        "verbose_lvl": verbose_lvl,
        "demos": demos,
        "plugins": plugins,
        "nocolors": nocolors,
        "noglyph": noglyph,
        "formatstyle": formatstyle,
        "benchmarking": benchmarking,
        "benchmarking_mods": benchmarking_mods,
        "colors": colors,
        "e3lm_parser": e3lm_parser,
    }

    # --- Check if benchmarking ---
    if benchmarking != False:
        if type(benchmarking) == list:
            if len(benchmarking) == 0:
                benchmarking = [1, 1, ]
            elif len(benchmarking) == 1:
                benchmarking.append(1)
        if benchmarking[0] != 0 and benchmarking[1] != 0:
            BENCHMARK(input_file, kwargs=kwargs)
    else:
        # --- Actual program ---
        CLI(input_file, kwargs=kwargs)


if __name__ == "__main__":
    main()
