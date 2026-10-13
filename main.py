Options:
    -i, --interactive   Open an interactive session.
    -s, --startup file  Run commands from file to initialize calculator before
                        any script or interactive session is run, stack is
                        cleared after it is run.
    -c, --nocolor       Do not color the output.
    -v, --verbose       Narrate the execution of any scripts.
    -V, --version       Print the ec version information.
    -h, --help          Print usage information.
"""
 
from .actions import (
    actionsToUse,
    defaultFormat,
    defaultDigits,
    defaultSpacer,
    predefinedVariables,
)
from .calculator import Calculator, Display, CalculatorError, __version__, __released__
from docopt import docopt
from inform import Color, display, error, fatal, Inform, os_error, warn, terminate
from os.path import expanduser, exists
import readline
 
 
def main():
    options = docopt(__doc__)
    scripts = options["<script>"]
    scheme = None if options["--nocolor"] else "dark"
    startup_files = [options["--startup"]] if options["--startup"] else []
    interactive = options["--interactive"] or not scripts
    verbose = options["--verbose"]
    Inform(prog_name=False, colorscheme=scheme)
 
    if options["--version"]:
        display("ec version: {} ({})".format(__version__, __released__))
        terminate()
 
    highlight = Color("magenta", scheme=scheme)
 
    def run_line(calc, line, prompt, location=None):
        try:
            result = calc.evaluate(calc.split(line))
            prompt = calc.format(result)
        except CalculatorError as e:
            if interactive:
                error(e.message, culprit=location)
                prompt = calc.restoreStack()
            else:
                fatal(e.message, culprit=location)
        return prompt
 
    calc = Calculator(
        actions=actionsToUse,
        formatter=Display(
            formatter=defaultFormat, digits=defaultDigits, spacer=defaultSpacer
        ),
        predefinedVariables=predefinedVariables,
        backUpStack=interactive,
        warningPrinter=lambda warning: None,
    )
    prompt = "0"
 
    rc_files = [f"{d}/.ecrc" for d in ["~", "."]]
    for each in rc_files + startup_files:
        lineno = None
        try:
            path = expanduser(each)
            with open(path) as f:
                for lineno, line in enumerate(f):
                    prompt = run_line(calc, line, prompt)
                    if verbose:
                        display(f"{path} {lineno}: {line.strip()} ==> {prompt}")
        except OSError as e:
            if each not in rc_files:
                fatal(os_error(e), culprit=(each, lineno))
 
    calc.stack.clear()
    prompt = "0"
 
    for arg in scripts:
        try:
            path = expanduser(arg)
            if exists(path):
                with open(path) as f:
                    for lineno, line in enumerate(f):
                        location = f"{path}s.{lineno + 1}"
                        prompt = run_line(calc, line, prompt, location)
                        if verbose:
                            display(f"{path} {lineno}: {line.strip()} ==> {prompt}")
            else:
                prompt = run_line(calc, arg, prompt)
                if verbose:
                    display(f"{arg} ==> {prompt}")
        except OSError as e:
            fatal(os_error(e), culprit=(each, lineno))
 
    if interactive:
        calc.warningPrinter = warn
 
        while True:
            try:
                entered = input(f"{highlight(prompt)}: ")
            except (EOFError, KeyboardInterrupt, SystemError):
                display()
                terminate()
            prompt = run_line(calc, entered, prompt)
 
    display(prompt)
    terminate()
 
