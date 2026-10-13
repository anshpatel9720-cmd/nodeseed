# Copyright (C) 2013-2024 Kenneth S. Kundert
# Licensed under the GNU General Public License v3 or later.

from copy import copy
from inform import Error, cull, display, full_stop, plural, warn
from pydoc import pager
from quantiphy import Quantity, UnitConversion, UnknownConversion
from textwrap import wrap, fill, dedent
import math
import re
import sys

__version__ = "1.11"
__released__ = "2024-08-06"

italicsRegex = re.compile(r"#⟪(\w+)⟫")
boldRegex = re.compile(r"@⟪(\w+)⟫")


def stripFormatting(text):
    text = italicsRegex.sub(r"\1", text)
    text = boldRegex.sub(r"\1", text)
    return text


def de_quote(text):
    if (text[0], text[-1]) == ('"', '"'):
        return text[1:-1]
    else:
        return text


class CalculatorError(Exception):
    def __init__(self, message):
        self.message = message

    def getMessage(self):
        return self.message


class Stack:
    def __init__(self, parent, stack=None):
        self.parent = parent
        if stack is None:
            stack = []
        self.stack = stack

    def push(self, value):
        self.parent.update_last_x = True
        self.stack.insert(0, value)

    def pop(self):
        try:
            return self.stack.pop(0)
        except IndexError:
            return (0, "")

    def peek(self, reg=0):
        try:
            return self.stack[reg]
        except IndexError:
            return (0, "")

    def clear(self):
        self.stack = []

    def clone(self):
        return Stack(self.parent, copy(self.stack))

    def __str__(self):
        return str(self.stack)

    def display(self):
        length = len(self.stack)
        labels = ["x:", "y:"] + (length - 2) * ["  "]
        for label, value in reversed(list(zip(labels, self.stack))):
            self.parent.printMessage(f"  {label} {self.parent.format(value)}")


class Heap:
    def __init__(self, parent=None, initialState=None, reserved=[], removeAction=None):
        self.parent = parent
        self.initialState = initialState if initialState is not None else {}
        self.reserved = list(reserved)
        self.heap = copy(self.initialState)
        self.removeAction = removeAction

    def clear(self):
        self.heap = copy(self.initialState)

    def __str__(self):
        return str(self.heap)

    def display(self):
        for key in sorted(self.heap.keys()):
            kind, value = self.heap[key]
            if kind == "const":
                self.parent.printMessage(f"  {key}: {self.parent.format(value)}")
            elif kind == "funct":
                self.parent.printMessage(f"  {key}: ({' '.join(value)})")
            else:
                raise NotImplementedError

    def __getitem__(self, key):
        return self.heap[key]

    def __setitem__(self, key, pair):
        kind, value = pair
        if key in self.reserved:
            if self.removeAction:
                self.parent.printWarning(f"{key}: variable has overridden built-in.")
                del self.reserved[self.reserved.index(key)]
                self.removeAction(key)
            else:
                raise KeyError
        self.heap[key] = kind, value

    def __contains__(self, key):
        return key in self.heap


class Display:
    def __init__(self, formatter, digits=4, spacer=" "):
        self.defaultFormatter = formatter.formatter
        self.defaultFormatterTakesUnits = formatter.formatterTakesUnits
        self.defaultDigits = digits
        self.formatter = formatter.formatter
        self.formatterTakesUnits = formatter.formatterTakesUnits
        self.digits = digits
        self.spacer = spacer

    def setFormatter(self, formatter):
        self.formatter = formatter.formatter
        self.formatterTakesUnits = formatter.formatterTakesUnits

    def setDigits(self, digits):
        self.digits = digits

    def format(self, val):
        num, units = val
        if isinstance(num, complex):
            real = self.format((num.real, units))
            imag = self.format((num.imag, units))
            zero = self.format((0, units))
            one = self.format((1, units))
            units = " " + units if units else ""

            if imag == zero:
                return real
            elif imag[0] == "-":
                imag = imag[1:] if imag[1:] != one else units.strip()
                if imag == zero:
                    return real
                if real == zero:
                    return "-j" + imag
                return f"{real} - j{imag}"
            else:
                imag = imag if imag != one else units
                if real == zero:
                    return "j" + imag
                return f"{real} + j{imag}"

        if self.formatterTakesUnits:
            return self.formatter(num, units, self.digits)
        else:
            number = self.formatter(num, self.digits)
            if units == "$":
                return units + number
            elif units == "":
                return number
            else:
                return number + self.spacer + units

    def clear(self):
        self.formatter = self.defaultFormatter
        self.formatterTakesUnits = self.defaultFormatterTakesUnits
        self.digits = self.defaultDigits


class Action:
    def __init__(self):
        raise NotImplementedError

    def getName(self, givenName=None):
        if hasattr(self, "name") and self.name:
            primaryName = self.name
        elif hasattr(self, "key") and self.key:
            primaryName = self.key
        else:
            primaryName = None

        if givenName:
            if hasattr(self, "name") and givenName == self.name:
                return primaryName
            if hasattr(self, "key") and givenName == self.key:
                return primaryName
            if hasattr(self, "aliases") and givenName in self.aliases:
                return primaryName
            return None
        else:
            return primaryName

    def getDescription(self):
        try:
            return self.description if self.description else ""
        except AttributeError:
            return ""

    def getSynopsis(self):
        try:
            return self.synopsis if self.synopsis else ""
        except AttributeError:
            return ""

    def getSummary(self):
        try:
            return self.summary if self.summary else ""
        except AttributeError:
            return ""

    def addAliases(self, aliases):
        try:
            self.aliases |= set(aliases)
        except AttributeError:
            self.aliases = set(aliases)

    def getAliases(self):
        try:
            return self.aliases
        except AttributeError:
            return set()

    def addTest(
        self,
        stimulus,
        result=None,
        units=None,
        text=None,
        error=None,
        messages=None,
        warnings=None,
    ):
        test = {"stimulus": stimulus}
        if result is not None:
            test["result"] = result
        if units is not None:
            test["units"] = units
        if text is not None:
            test["text"] = text
        if error is not None:
            test["error"] = error
        if messages is not None:
            test["messages"] = [messages] if isinstance(messages, str) else messages
        if warnings is not None:
            test["warnings"] = warnings if isinstance(warnings, list) else [warnings]

        if hasattr(self, "tests"):
            self.tests += [test]
        else:
            self.tests = [test]

        misplacedTest = f"misplaced test: action={self.getName()}, stimulus={stimulus}"
        components = Calculator.split(stimulus)
        if hasattr(self, "key"):
            found = self.key in components
            if not found and hasattr(self, "name"):
                found = any(c.startswith(self.key) for c in components)

            if not found and hasattr(self, "aliases"):
                found = set(self.aliases).intersection(set(components))
        elif hasattr(self, "regex"):
            found = False
            for each in components:
                if self.regex.match(each):
                    found = True
                    break
        assert found, misplacedTest


class Command(Action):
    def __init__(
        self,
        key,
        action,
        name=None,
        description=None,
        synopsis=None,
        summary=None,
        aliases=frozenset(),
    ):
        self.key = key
        self.action = action
        self.name = name
        self.description = description
        self.synopsis = synopsis
        self.summary = summary
        self.aliases = aliases

    def _execute(self, calc):
        self.action(calc)


class Constant(Action):
    def __init__(
        self,
        key,
        action,
        description=None,
        units="",
        synopsis=None,
        summary=None,
        aliases=frozenset(),
    ):
        self.key = key
        self.action = action
        self.description = description
        self.units = units
        self.synopsis = synopsis
        self.summary = summary
        self.aliases = aliases

    def _execute(self, calc):
        stack = calc.stack
        if isinstance(self.action, dict):
            try:
                result, units = self.action[calc.unit_system]
            except KeyError:
                raise CalculatorError(
                    f"{self.key}: {calc.unit_system} version unavailable."
                )
        elif type(self.action) is tuple:
            result, units = self.action
        else:
            result, units = self.action, ""
        if callable(result):
            result = result()
        stack.push((result, units))


class UnaryOp(Action):
    def __init__(
        self,
        key,
        action,
        description=None,
        needCalc=False,
        units="",
        synopsis=None,
        summary=None,
        aliases=frozenset(),
    ):
        self.key = key
        self.action = action
        self.description = description
        self.needCalc = needCalc
        self.units = units
        self.synopsis = synopsis
        self.summary = summary
        self.aliases = aliases

    def _execute(self, calc):
        stack = calc.stack
        x, xUnits = stack.pop()
        if self.needCalc:
            x = self.action(x, calc)
        else:
            x = self.action(x)
        if callable(self.units):
            units = self.units(calc, (xUnits,))
        else:
            units = self.units
        stack.push((x, units))


class BinaryOp(Action):
    def __init__(
        self,
        key,
        action,
        description=None,
        needCalc=False,
        units="",
        synopsis=None,
        summary=None,
        aliases=frozenset(),
    ):
        self.key = key
        self.action = action
        self.description = description
        self.needCalc = needCalc
        self.units = units
        self.synopsis = synopsis
        self.summary = summary
        self.aliases = aliases

    def _execute(self, calc):
        stack = calc.stack
        x, xUnits = stack.pop()
        y, yUnits = stack.pop()
        if self.needCalc:
            result = self.action(y, x, calc)
        else:
            result = self.action(y, x)
        if callable(self.units):
            units = self.units(calc, (xUnits, yUnits))
        else:
            units = self.units
        stack.push((result, units))


class BinaryIoOp(Action):
    def __init__(
        self,
        key,
        action,
        description=None,
        needCalc=False,
        xUnits="",
        yUnits="",
        synopsis=None,
        summary=None,
        aliases=frozenset(),
    ):
        self.key = key
        self.action = action
        self.description = description
        self.needCalc = needCalc
        self.xUnits = xUnits
        self.yUnits = yUnits
        self.synopsis = synopsis
        self.summary = summary
        self.aliases = aliases

    def _execute(self, calc):
        stack = calc.stack
        x, xUnits = stack.pop()
        y, yUnits = stack.pop()
        if self.needCalc:
            result = self.action(y, x, calc)
        else:
            result = self.action(y, x)
        if callable(self.xUnits):
            xUnits = self.xUnits(calc, (xUnits, yUnits))
        else:
            xUnits = self.xUnits
        if callable(self.yUnits):
            yUnits = self.yUnits(calc, (xUnits, yUnits))
        else:
            yUnits = self.yUnits
        stack.push((result[1], yUnits))
        stack.push((result[0], xUnits))


class Dup(Action):
    def __init__(
        self,
        key,
        action,
        description=None,
        needCalc=False,
        units="",
        synopsis=None,
        summary=None,
        aliases=frozenset(),
    ):
        self.key = key
        self.action = action
        self.description = description
        self.summary = summary
        self.needCalc = needCalc
        self.units = units
        self.synopsis = synopsis
        self.summary = summary
        self.aliases = aliases

    def _execute(self, calc):
        stack = calc.stack
        x, xUnits = stack.peek()
        if self.action:
            if self.needCalc:
                x = self.action(x, calc)
            else:
                x = self.action(x)
            if self.units:
                if callable(self.units):
                    xUnits = self.units(calc, (xUnits,))
                else:
                    xUnits = self.units
        stack.push((x, xUnits))


class Number(Action):
    def __init__(
        self,
        pattern,
        action,
        name,
        description=None,
        needCalc=False,
        synopsis=None,
        summary=None,
    ):
        self.pattern = pattern
        self.action = action
        self.name = name
        self.description = description
        self.needCalc = needCalc
        self.synopsis = synopsis
        self.summary = summary
        self.regex = re.compile(pattern)

    def _execute(self, matchGroups, calc):
        if self.needCalc:
            num, units = self.action(matchGroups, calc)
        else:
            num, units = self.action(matchGroups)
        calc.stack.push((num, units))


class SetFormat(Action):
    def __init__(
        self,
        pattern,
        action,
        name,
        actionTakesUnits=False,
        description=None,
        summary=None,
    ):
        self.pattern = pattern
        self.formatter = action
        self.name = name
        self.formatterTakesUnits = actionTakesUnits
        self.description = description
        self.summary = summary
        self.regex = re.compile(pattern)

    def _execute(self, matchGroups, calc):
        calc.formatter.setFormatter(self)
        if matchGroups and matchGroups[0] is not None:
            calc.formatter.setDigits(int(matchGroups[0]))


class Help(Action):
    def __init__(self, key=None, name=None, description=None, summary=None):
        assert key or name
        self.key = key
        self.name = name
        self.description = description
        self.summary = summary
        self.regex = re.compile(r"\?(\S+)?")

    def _execute(self, matchGroups, calc):
        topic = matchGroups[0]

        if topic:
            for action in calc.actions:
                found = action.getName(topic)
                if found:
                    summary = action.getSummary()
                    synopsis = stripFormatting(action.getSynopsis())
                    aliases = action.getAliases()
                    if aliases:
                        aliases = f"{plural(aliases):alias/es}: {','.join(aliases)}"
                    if action.description:
                        calc.printMessage(
                            fill(
                                stripFormatting(action.description.format(**action.__dict__)),
                                subsequent_indent="    ",
                            )
                        )
                    else:
                        calc.printMessage(found + ":")
                    if summary:
                        calc.printMessage()
                        calc.printMessage(self.formatHelpText(summary))
                    if synopsis or aliases:
                        calc.printMessage()
                    if synopsis:
                        calc.printMessage(f"stack: {synopsis}")
                    if aliases:
                        calc.printMessage(aliases)
                    return
            calc.printWarning(f"{topic}: not found.\n")

        topics = [action.getName() for action in calc.actions if action.getName()]
        colWidth = max([len(topic) for topic in topics]) + 3
        topics.sort()
        calc.printMessage("For summary of all topics, use 'help'.")
        calc.printMessage("For help on a particular topic, use '?topic'.")
        calc.printMessage()
        calc.printMessage("Available topics:")
        numCols = 78 // colWidth
        numRows = (len(topics) + numCols - 1) // numCols
        cols = []
        for i in range(numCols):
            cols.append(topics[i * numRows : (i + 1) * numRows])
        for i in range(len(cols[0])):
            for j in range(numCols):
                try:
                    calc.printMessage(
                        "{0:{width}s}".format(cols[j][i], width=colWidth),
                        style="fragment",
                    )
                except IndexError:
                    pass
            calc.printMessage()
        return

    def formatHelpText(self, text):
        lines = dedent(text).strip().splitlines()
        paragraphs = []
        gatheredLines = []
        verbatim = False
        for line in lines:
            if line.strip() == r"\verb⟪":
                verbatim = True
                paragraphs += [fill(" ".join(gatheredLines))]
                gatheredLines = []
            elif line.strip() == "⟫":
                verbatim = False
            else:
                line = stripFormatting(line)
                if verbatim:
                    paragraphs += [line.rstrip()]
                else:
                    gatheredLines += [line.strip()]
        if gatheredLines:
            paragraphs += [fill(" ".join(gatheredLines))]
        return "\n".join(paragraphs)


class Store(Action):
    def __init__(self, name, description=None, synopsis=None, summary=None):
        self.name = name
        self.description = description
        self.synopsis = synopsis
        self.summary = summary
        self.regex = re.compile(r"=([a-z]\w*)", re.I)

    def _execute(self, matchGroups, calc):
        name = matchGroups[0]
        try:
            calc.heap[name] = "const", calc.stack.peek()
        except KeyError:
            raise CalculatorError(
                f"{name}: reserved, cannot be used as variable name."
            )


class Recall(Action):
    def __init__(self, name, description=None, synopsis=None, summary=None):
        self.name = name
        self.description = description
        self.synopsis = synopsis
        self.summary = summary
        self.regex = re.compile(r"([a-z]\w*)", re.I)

    def _execute(self, matchGroups, calc):
        name = matchGroups[0]
        if name in calc.heap:
            kind, value = calc.heap[name]
            if kind == "const":
                calc.stack.push(value)
            elif kind == "funct":
                calc.evaluate(value)
            else:
                raise NotImplementedError
        else:
            raise CalculatorError(f"{name}: variable does not exist.")


class SetUnits(Action):
    def __init__(self, name, key=None, description=None, synopsis=None, summary=None):
        self.key = key
        self.name = name
        self.description = description
        self.synopsis = synopsis
        self.summary = summary
        self.regex = re.compile(r'"(.*)"')

    def _execute(self, matchGroups, calc):
        stack = calc.stack
        (units,) = matchGroups
        x, xUnits = stack.pop()
        stack.push((x, units))


class Convert(Action):
    def __init__(self, key, name=None, description=None, synopsis=None, summary=None):
        self.key = key
        self.name = name
        self.description = description
        self.synopsis = synopsis
        self.summary = summary
        self.regex = re.compile(r'>([a-z$°ÅɃ₿ș]\w*)', re.I)

    def _execute(self, matchGroups, calc):
        to_units = de_quote(matchGroups[0])
        stack = calc.stack
        x, xUnits = stack.pop()

        try:
            if xUnits:
                x = Quantity(x, xUnits).scale(to_units)
                xUnits = x.units
            else:
                xUnits = to_units
        except UnknownConversion as e:
            raise Error(e, culprit=(xUnits, to_units))

        stack.push((x, xUnits))


class Print(Action):
    def __init__(self, key=None, name=None, description=None, summary=None):
        assert key or name
        self.key = key
        self.name = name
        self.description = description
        self.summary = summary
        self.regex = re.compile(r"`(.*)`")
        self.argsRegex = re.compile(r"\${?(\w+|\$)}?")

    def _execute(self, matchGroups, calc):
        (text,) = matchGroups
        if not text:
            message = calc.format(calc.stack.stack[0])
        else:
            text = text.replace(r"\n", "\n")
            text = text.replace(r"\t", "\t")
            components = self.argsRegex.split(text)
            args = components[1::2]
            formattedArgs = []
            for arg in args:
                try:
                    try:
                        arg = calc.stack.stack[int(arg)]
                    except ValueError:
                        kind, value = calc.heap[arg]
                        if kind == "const":
                            arg = value
                        elif kind == "funct":
                            raise CalculatorError(
                                f"{value}s: cannot print a function."
                            )
                        else:
                            raise NotImplementedError
                    arg = calc.format(arg)
                except (KeyError, IndexError):
                    if arg != "$":
                        if calc.warningPrinter:
                            calc.warningPrinter(f"${arg}: unknown.")
                        arg = f"$?{arg}?"
                formattedArgs += [arg]
            components[1::2] = formattedArgs
            message = "".join(components)
        calc.printMessage(message)


class Category(Action):
    def __init__(self, description):
        self.category = description
        self.description = description


class Calculator:
    operatorSplitRegex = re.compile(
        r"""
        (?<=[a-zA-Z0-9°ÅΩƱΩ℧µμ])
        (?=([-+*/%!]|\*\*|\|\||//)(\s|\Z))
    """,
        re.X,
    )
    stringSplitRegex = re.compile(r"""((?:"[^"]*"|`[^`]*`)+)""")

    def __init__(
        self,
        actions,
        formatter,
        predefinedVariables={},
        backUpStack=False,
        messagePrinter=None,
        warningPrinter=None,
    ):
        alreadySeen = set()
        prunedActions = []
        self.smplActions = {}
        self.regexActions = []
        names = set()
        for action in actions:
            if not action:
                continue
            elif hasattr(action, "regex"):
                if action.regex not in alreadySeen:
                    self.regexActions += [action]
                    prunedActions += [action]
                    alreadySeen.add(action.regex)
                    assert action.name not in self.smplActions, (
                        f"{action.name}: duplicate name"
                    )
                    names.add(action.name)
            elif hasattr(action, "key"):
                if action.key not in alreadySeen:
                    self.smplActions.update({action.key: action})
                    prunedActions += [action]
                    alreadySeen.add(action.key)
                    assert action.key not in names, f"{action.key}: duplicate name"
                    names.add(action.key)
                    for alias in action.getAliases():
                        assert alias not in names, f"{alias}: duplicate name"
                        names.add(alias)
                        self.smplActions.update({alias: action})
            else:
                assert hasattr(action, "category"), f"expected category: {action.__dict__}"
                prunedActions += [action]
        self.actions = prunedActions

        self.formatter = formatter
        self.backUpStack = backUpStack
        self.messagePrinter = messagePrinter
        self.warningPrinter = warningPrinter
        self.stack = Stack(parent=self)
        self.function = None
        self.functions = {}
        self.heap = Heap(
            initialState=predefinedVariables,
            reserved=self.smplActions.keys(),
            removeAction=self.removeAction,
            parent=self,
        )
        self.clear()

    @classmethod
    def split(cls, given):
        processed = given.replace("(", "( ").replace(")", " )")

        components = Calculator.stringSplitRegex.split(processed)
        tokens = []
        for i, component in enumerate(components):
            if i % 2:
                tokens += [component]
            else:
                tokens += Calculator.operatorSplitRegex.sub(" ", component).split()
        return tokens

    def evaluate(self, given):
        def showLoc(given, index):
            cmds = " ".join(given)
            okay = " ".join(given[:index])
            return "\n" + cmds + "\n " + " " * len(okay) + "▲"

        if self.backUpStack:
            self.prevStack = self.stack.clone()
        try:
            for index, cmd in enumerate(given):
                last_x = self.stack.peek()
                self.update_last_x = False
                if self.function is not None:
                    if cmd == "(":
                        raise Error("nested function definitions.")
                    elif cmd[0] == ")":
                        name = cmd[1:]
                        nameRegex = r"[a-zA-Z_]\w*"
                        if not re.match(nameRegex, name):
                            raise Error(f"{name}: invalid function name.")
                        if name in self.heap:
                            k, v = self.heap[name]
                            if k != "funct":
                                raise Error(f"{name}: name is reserved.")
                        self.heap[name] = "funct", self.function
                        self.function = None
                    else:
                        self.function.append(cmd)
                else:
                    if cmd == "(":
                        self.function = []
                    elif cmd in self.smplActions:
                        self.smplActions[cmd]._execute(self)
                    else:
                        for action in self.regexActions:
                            match = action.regex.match(cmd)
                            if match:
                                action._execute(match.groups(), self)
                                break
                        else:
                            if cmd == "#":
                                break
                            raise Error(f"{cmd}: unrecognized.")
                if self.update_last_x:
                    self.last_x = last_x
            return self.stack.peek()
        except TypeError as e:
            if str(e).startswith("can't convert complex to float"):
                raise CalculatorError(
                    "must be real number, not complex."
                    + showLoc(given, index)
                )
            else:
                raise CalculatorError(full_stop(e) + showLoc(given, index))
        except ZeroDivisionError:
            raise CalculatorError("division by zero." + showLoc(given, index))
        except (ValueError, OverflowError, Error) as e:
            raise CalculatorError(full_stop(e) + showLoc(given, index))

    def clear(self):
        self.stack.clear()
        self.prevStack = None
        self.last_x = (0, "")
        self.formatter.clear()
        self.heap.clear()
        self.useDegrees()
        self.useMKS()

    def restoreStack(self):
        self.stack = self.prevStack
        return self.format(self.stack.peek())

    def format(self, value):
        return self.formatter.format(value)

    def removeAction(self, key):
        del self.smplActions[key]

    def useMKS(self):
        self.unit_system = "mks"

    def useCGS(self):
        self.unit_system = "cgs"

    def useRadians(self):
        self.trigMode = "rads"
        self.convertToRadians = 1

    def useDegrees(self):
        self.trigMode = "degs"
        self.convertToRadians = math.pi / 180

    def toRadians(self, arg):
        return arg * self.convertToRadians

    def fromRadians(self, arg):
        return arg / self.convertToRadians

    def angleUnits(self):
        return self.trigMode

    def swap(self):
        stack = self.stack
        x, xUnits = stack.pop()
        y, yUnits = stack.pop()
        stack.push((x, yUnits))
        stack.push((y, yUnits))

    def pop(self):
        self.stack.pop()

    def printMessage(self, message="", style="line"):
        if self.messagePrinter:
            self.messagePrinter(message, style)
        else:
            if style == "page":
                pager(message)
            elif style == "line":
                display(message)
            else:
                assert style == "fragment"
                display(message, end=" ")

    def printWarning(self, warning):
        if self.warningPrinter:
            self.warningPrinter(warning)
        else:
            warn(warning)

    def displayHelp(calc):
        lines = []
        for action in calc.actions:
            if action.description:
                if hasattr(action, "category"):
                    lines += ["\n" + action.description.format(**action.__dict__)]
                else:
                    lines += wrap(
                        stripFormatting(action.description.format(**action.__dict__)),
                        initial_indent="    ",
                        subsequent_indent="        ",
                    )

                    aliases = action.getAliases()
                    if aliases:
                        aliases = f"{plural(aliases):alias/es}: {', '.join(aliases)}"
                    help_name = getattr(action, 'name', None) or getattr(action, 'key', None)
                    help_name = f"help: ?{help_name}" if help_name else ""
                    addendum = "; ".join(cull([aliases, help_name]))
                    if addendum:
                        lines.append(f"        {addendum}")
        calc.printMessage("\n".join(lines) + "\n", style="page")

    def aboutMsg(calc):
        calc.printMessage(
            dedent(
                """\
            EC: Engineering Calculator
            Version {} ({}).

            EC was written by Ken Kundert.
            Report issues or ask questions at https://github.com/KenKundert/ec/issues
            To view the manual, visit https://engineering-calculator.readthedocs.io\
        """.format(
                    __version__, __released__
                )
            )
        )

    def describeFunctions(calc):
        calc.printMessage(
            dedent(
                """
            Define functions using:
                ( ... )name

            Here '(' starts the function definition and ')name' ends it. The
            closing parenthesis must be immediately adjacent to 'name'. The
            '...' represents a sequence of calculator actions. For example:

                0: (2pi * “rads/s”)to_omega
                0: (2pi / “Hz”)to_freq
                0: 100MHz
                100 MHz: to_omega
                628.32 Mrads/s: to_freq
                100 MHz:

            You can list the user-defined functions along with the user-defined
            variables using the 'vars' command. The functions are delimited with
            parentheses.
        """
            ).strip()
        )

    def quit(calc):
        sys.exit(0)
