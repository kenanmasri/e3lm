# -*- coding=utf-8 -*-
"""The e3lm CLI tool (3lm language) for managing 3lm projects and files.

This tool is designed mainly to enable interpretation of 3lm files and upgrading
the interpreter and its plugins.
"""

__doc2__ = """additional arguments:
    nothing for now.
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
import textwrap
import os
import subprocess
import io
import signal
import sys
import tempfile
import json
import timeit
import pipes
from datetime import datetime
from time import sleep
from time import perf_counter

from utils.spin import animate as spinner
from helpers import printers
from helpers.printers import COLORS as COLS
from lang.ast import basic_dt
from utils.lang import lex, parse, interpret
from lang.interpreters import E3lmInterpreter, E3lmPlugin
from contrib.json import JsonPlugin as Json
from contrib.dot import DotPlugin as Dot
from graphviz import Source as GraphvizSource
from tests.data import getcode as gettestcode

# Colors enabler
import colorama
from io import StringIO
from colorama import Fore, Style
import itertools


def windows_enable_ANSI(std_id):
    """Enable Windows 10 cmd.exe ANSI VT Virtual Terminal Processing."""
    from ctypes import byref, POINTER, windll, WINFUNCTYPE
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


def get_plugin(string):
    if str(string).lower() == "json":
        return Json
    if str(string).lower() == "dot":
        return Dot
    return str(string).lower()


def CLI(input_file="-"):
    """The actual CLI"""
    global COLS
    shown_msgs = {}
    runstack = {}
    runtime = {}
    special_positionals = ("?", "help",  # Help alternatives.
                           "-", ".",  # No or all file(s)
                           )
    # Repopulate some settings
    if nocolors:
        COLS = {k: "" for k in COLS.keys()}

    # TODO Add a home directory instead
    # Cancelled: Initiate a persistent temporary directory if we did not yet.
    # tmpdir = tempfile.gettempdir() + os.pathsep + "e3lm" + os.pathsep + "py"
    # if not os.path.exists(tmpdir):
    #     os.mkdir(tmpdir)
    # tmpfileid = "session-" + datetime.strftime(datetime.now(), "%Y-m%#D")

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
                if not quiet:
                    print(COLS["E"] + 'Error: ' + input_file +
                          ' does not exist.' + COLS["R"], file=sys.stderr)
            elif not quiet:
                print(COLS["E"] + 'Error: ' + input_file +
                      ' is a directory.' + COLS["R"], file=sys.stderr)
            sys.exit(1)

    # Check if demos are specified
    if len(demos) > 0:
        runstack.update({d: demo_file(d) for d in demos if demo_exists(d)})

    # Load up each stack content (file or directly)
    for key, val in runstack.items():
        if os.path.isfile(val) and os.path.exists(val):
            try:
                f = open(val)
                d = "".join(f.readlines())
                if benchmarking_mods["enabled"]:
                    d = (d + "\n") * int(benchmarking_mods["lengthofcode"])
            finally:
                f.close()
        else:
            d = val

        runtime[key] = d

    # Print headers for each runtime
    for i, run in runtime.items():
        printers.cprint(COLS["3"] + "--" + COLS["1"] + "== " + COLS["4"] +
                        i + COLS["1"] + " ==" + COLS["3"] + "--" + COLS["R"], col="SUCCESS")

        run_plugins = [get_plugin(p) for p in plugins if type(
            get_plugin(p)) not in basic_dt]

        if "lex" in plugins:
            run_program = lex(run, i, debug=verbose_lvl >= 2,
                              enable_colors=nocolors == False, tracking=verbose_lvl >= 2)

        if "parse" in plugins:
            run_program = parse(run, parser_kwargs={
                "tracking": verbose_lvl >= 2,
                "enable_colors": nocolors == False,
                "debug": verbose_lvl >= 2,
            }, debug=verbose_lvl >= 3)
            if verbose_lvl >= 2:
                if not benchmarking_mods["enabled"]:
                    printers.nprint(run_program, max_level=0, colors_enabled=nocolors ==
                                    False, program_name=i, evaluate=False)
                else:
                    if "benchmarking_parse" not in shown_msgs.keys():
                        shown_msgs["benchmarking_parse"] = True
                        print(COLS["2"] + "       - "+COLS["H"] + str(
                            len(run.splitlines())) + " line(s) of code Total." + COLS["R"])

        run_program = interpret(run,
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
                printers.nprint(run_program, max_level=0, colors_enabled=nocolors ==
                                False, program_name=i, evaluate=True)
            else:
                if "benchmarking_parse" not in shown_msgs.keys():
                    shown_msgs["benchmarking_parse"] = True
                    print(COLS["2"] + "       - "+COLS["H"] +
                          str(len(run.splitlines())) + " line(s) of code Total." + COLS["R"])
                if "benchmarking_intr" not in shown_msgs.keys():
                    shown_msgs["benchmarking_intr"] = True
                    print(COLS["2"] + "       - "+COLS["H"] +
                          str(len(run_program.flat_blocks)) + " blocks(s) Total." + COLS["R"])

        if "benchmarking_parse" in shown_msgs.keys():
            del shown_msgs["benchmarking_parse"]
        if "benchmarking_intr" in shown_msgs.keys():
            del shown_msgs["benchmarking_intr"]

        if run_program == None:
            print("None")
        if "json" in plugins:
            print(json.dumps(run_program.json, indent=4))
        if "view" in plugins:
            if run_program:
                graph = GraphvizSource(run_program.dot_source, filename="tmp/"+i+".dot", format="png")
                graph.view()
            else:
                print("Nothing to view")

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


def BENCHMARK(input_file):
    import math
    shown_msgs = {}
    py = os.getenv("WORKSPACE") + os.path.sep + os.getenv("VENV_NAME") + \
        os.path.sep + "Scripts" + os.path.sep + "python"
    printers.cprint(COLS["2"] + "--" + COLS["2"] + "== " + COLS["2"] +
                    "Benchmarking..." + COLS["2"] + " ==" + COLS["2"] + "--" + COLS["R"], col="SUCCESS")

    sys_argv_ = sys.argv
    sys_argv_.pop(0)
    sys_argv_.append("--benchmark-mods")
    sys_argv_.append(
        "lengthofcode="+str(benchmarking[1])+","
        + "iterations="+str(benchmarking[0])+""
    )

    iterations = 0
    err_count = 0
    timelog = []

    while iterations < int(benchmarking[0]):
        # Open a subprocess for running the wanted command...
        try:
            # Remove the benchmark arguments and pass the rest to the caller.
            testto = e3lm_parser.parse_args()
            testto.benchmarking = benchmarking
            strings = sys_argv_
            for string in strings:
                if string == "-b" or string == "--benchmark":
                    pos = strings.index(string)+1
                    if testto.benchmarking[0] != 0:
                        if testto.benchmarking[0] == strings[pos]:
                            strings.pop(pos)
                            pos -= 1
                    if testto.benchmarking[1] != 0:
                        if testto.benchmarking[1] == strings[pos+1]:
                            strings.pop(pos+1)
                            pos -= 1
                    strings.remove(string)
                    break

            call = " ".join([pipes.quote(s) for s in strings])
            if verbose_lvl == 3:
                if "dbg_benchmark_init" not in shown_msgs.keys():
                    print(COLS["BLUE"] + "DBG: The call in subprocess is: " +
                          COLS["CYAN"] + "python e3lm.py " + call)
            p = caller("\"" + py + "\"" + " " + "\"" + os.path.abspath(__file__) +
                       "\" " + call, _type="subprocess", shell=False, ret=True)
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
                        print(COLS["2"] + "       OUT: "+COLS["R"] + read_pout)
                    if read_perr != "":
                        print(COLS["E"] + "       ERR: "+COLS["R"] + read_perr)
                        raise TimeoutError("An error occured, aborting..")
                if p.poll() != None:
                    shown_msgs["benchmark_first_iteration"] = True
                    break
                else:
                    sys.stdout.write('\r' + c + ' ' +
                                     "inst: " + str(iterations) + "  ")
                    sys.stdout.flush()
                    sleep(0.033)
            t_end = perf_counter()
        except KeyboardInterrupt:
            print(COLS["GREEN"] +
                  "\nUser cancelled (KeyboardInterrupt)" + COLS["R"])
            printers.cprint(COLS["2"] + "--" + COLS["2"] + "== " + COLS["2"] +
                            "Benchmarking done..." + COLS["2"] + " ==" + COLS["2"] + "--" + COLS["R"] + "\n", col="SUCCESS")
            exit(0)
        except TimeoutError as e:
            print(COLS["GREEN"] + "Timeout: " + str(e) + COLS["R"])
            printers.cprint(COLS["2"] + "--" + COLS["2"] + "== " + COLS["2"] +
                            "Benchmarking done..." + COLS["2"] + " ==" + COLS["2"] + "--" + COLS["R"] + "\n", col="SUCCESS")
            exit(1)

        timelog.append({
            "iteration": iterations,
            "start": t_start,
            "end": t_end,
            "stdout": read_total_pout,
            "stderr": read_total_perr,
        })

        shown_msgs["dbg_benchmark_init"] = True
        iterations += 1

    sys.stdout.write('\r' + 'Total iterations: '+str(iterations)+'\n')
    sys.stdout.flush()

    [print(str(t["iteration"])+" => "+str(round((t["end"]-t["start"])
           * 1000, 1000))[:6]+" ms") for t in timelog]

    durations = [t["end"]-t["start"] for t in timelog]
    print(COLS["1"]+"Max: " + COLS["HEADER"] + str(round((max(durations))
          * 1000, 1000))[:6] + COLS["1"] + " ms" + COLS["R"])
    print(COLS["1"]+"Min: " + COLS["HEADER"] + str(round((min(durations))
          * 1000, 1000))[:6] + COLS["1"] + " ms" + COLS["R"])
    print(COLS["1"]+"Avg: " + COLS["HEADER"] + str(round((sum(durations) /
          iterations) * 1000, 1000))[:6] + COLS["1"] + " ms" + COLS["R"])
    printers.cprint(COLS["2"] + "--" + COLS["2"] + "== " + COLS["2"] +
                    "Benchmarking done..." + COLS["2"] + " ==" + COLS["2"] + "--" + COLS["R"] + "\n", col="SUCCESS")
    exit(0)


if __name__ == "__main__":
    e3lm_parser = argparse.ArgumentParser(prog='e3lm',
                                          usage='%(prog)s [options] file',
                                          description=__doc__,
                                          formatter_class=argparse.RawTextHelpFormatter,
                                          epilog=__doc2__)

    e3lm_parser.add_argument('--version', action="version",
                             version="e3lm v" + __version__ + " (3lm language)")

    e3lm_parser.add_argument('file',
                             nargs='?',
                             default='-',
                             help='path to the 3lm file (automatically detects extension) or - for nothing',
                             )

    e3lm_parser.add_argument('-q',
                             '--quiet',
                             action='store_true',
                             default=False,
                             help='run quietly without any output')

    e3lm_parser.add_argument('-nc',
                             '--no-color',
                             action='store_true',
                             dest="nocolors",
                             default=False,
                             help='set output to be without ANSI colors')

    e3lm_parser.add_argument('-v',
                             '--verbose',
                             action='store',
                             metavar='NONE/ERROR/INFO/DEBUG',
                             dest='verbose',
                             type=str,
                             choices=["NONE", "ERROR", "INFO", "DEBUG"],
                             default="INFO",
                             help='filter output messages (default is INFO)')

    e3lm_parser.add_argument('-i',
                             '--interactive',
                             action='store_true',
                             default=False,
                             help='execute with interactive mode')

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
                             help='interpret demos from tests in addition'
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

    # --- Check if benchmarking ---
    if benchmarking != False:
        if type(benchmarking) == list:
            if len(benchmarking) == 0:
                benchmarking = [1, 1, ]
            elif len(benchmarking) == 1:
                benchmarking.append(1)
        if benchmarking[0] != 0 and benchmarking[1] != 0:
            BENCHMARK(input_file)
    else:
        # --- Actual program ---
        CLI(input_file)
