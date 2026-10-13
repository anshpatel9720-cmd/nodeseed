import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from .actions import (
    actionsToUse,
    defaultFormat,
    defaultDigits,
    defaultSpacer,
    predefinedVariables,
)
from .calculator import Calculator, Display, CalculatorError

BG = "#1b1b21"
PANEL = "#26262e"
DISPLAY_BG = "#101014"
FG = "#ececf1"
MUTED = "#8b8b99"
ACCENT = "#4f8cff"
GOOD = "#7fdc8c"
WARN = "#f0c060"
BAD = "#ff7b7b"

BUTTON_STYLES = {
    "Num": ("#34343f", "#454552", FG),
    "Op": ("#3b4a6b", "#4a5c85", FG),
    "Fn": ("#2c2c35", "#3b3b47", FG),
    "Unit": ("#2d3a33", "#3b4b41", FG),
    "Clear": ("#6b3b3b", "#85494a", FG),
    "Enter": (ACCENT, "#6aa0ff", "#ffffff"),
}

FUNCTION_KEYS = [
    [("√", "sqrt"), ("x²", "sqr"), ("1/x", "recip"), ("|x|", "abs")],
    [("eˣ", "exp"), ("ln", "ln"), ("10ˣ", "pow10"), ("log", "log")],
    [("sin", "sin"), ("cos", "cos"), ("tan", "tan"), ("π", "pi")],
    [("asin", "asin"), ("acos", "acos"), ("atan", "atan"), ("2π", "2pi")],
    [("hypot", "hypot"), ("dB", "db"), ("dB→", "adb"), ("yˣ", "**")],
    [("swap", "swap"), ("dup", "dup"), ("pop", "pop"), ("clstk", "clstack")],
    [("DEG", "degs"), ("RAD", "rads"), ("lastx", "lastx"), ("vars", "vars")],
    [("SI", "si"), ("ENG", "eng"), ("SCI", "sci"), ("help", "help")],
]

PREFIX_KEYS = [["k", "M", "G", "m"], ["µ", "n", "p", "f"]]
UNIT_KEYS = [["V", "A", "Ω", "Hz"], ["F", "H", "s", "W"]]


class CalculatorApp:
    stackLabels = ["x", "y", "z", "t"]
    stackRows = 8

    def __init__(self, root):
        self.root = root
        self.history = []
        self.historyIndex = 0
        self.family = tkfont.nametofont("TkFixedFont").actual("family")
        self.calc = Calculator(
            actions=actionsToUse,
            formatter=Display(
                formatter=defaultFormat, digits=defaultDigits, spacer=defaultSpacer
            ),
            predefinedVariables=predefinedVariables,
            backUpStack=True,
            messagePrinter=self.printMessage,
            warningPrinter=self.printWarning,
        )
        self.setupStyles()
        self.buildWindow()
        self.refresh()
        self.entry.focus_set()

    def setupStyles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        for name, (background, hover, foreground) in BUTTON_STYLES.items():
            size = 11 if name == "Fn" else 13
            style.configure(
                f"{name}.TButton",
                background=background,
                foreground=foreground,
                font=(self.family, size, "bold"),
                borderwidth=0,
                focusthickness=0,
                focuscolor=background,
                padding=(4, 9),
                anchor="center",
            )
            style.map(
                f"{name}.TButton",
                background=[("pressed", hover), ("active", hover)],
            )
        style.configure(
            "Log.Vertical.TScrollbar",
            background=PANEL,
            troughcolor=DISPLAY_BG,
            bordercolor=DISPLAY_BG,
            arrowcolor=MUTED,
        )

    def buildWindow(self):
        self.root.title("EC Engineering Calculator")
        self.root.configure(bg=BG)
        self.root.geometry("1120x700")
        self.root.minsize(1000, 660)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0)
        self.root.rowconfigure(0, weight=1)

        left = tk.Frame(self.root, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(18, 9), pady=18)
        right = tk.Frame(self.root, bg=BG)
        right.grid(row=0, column=1, sticky="ns", padx=(9, 18), pady=18)

        self.buildDisplay(left)
        self.buildKeys(right)

        self.root.bind("<Return>", lambda event: self.submit())
        self.root.bind("<KP_Enter>", lambda event: self.submit())
        self.root.bind("<Escape>", lambda event: self.clearEntry())

    def buildDisplay(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)

        header = tk.Frame(parent, bg=BG)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        tk.Label(
            header, text="STACK", bg=BG, fg=MUTED, font=(self.family, 10, "bold")
        ).grid(row=0, column=0, sticky="w")
        self.modeLabel = tk.Label(
            header, text="", bg=BG, fg=ACCENT, font=(self.family, 10, "bold")
        )
        self.modeLabel.grid(row=0, column=1, sticky="e")

        self.stackView = tk.Text(
            parent,
            height=self.stackRows,
            bg=DISPLAY_BG,
            fg=FG,
            relief="flat",
            highlightthickness=0,
            padx=16,
            pady=12,
            font=(self.family, 20),
            state="disabled",
            cursor="arrow",
            spacing1=3,
            spacing3=3,
        )
        self.stackView.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        self.stackView.tag_configure("label", foreground=MUTED)
        self.stackView.tag_configure("value", foreground=FG)
        self.stackView.tag_configure("top", foreground=GOOD)
        self.stackView.bind("<Configure>", self.alignStack)

        tk.Label(
            parent, text="INPUT", bg=BG, fg=MUTED, font=(self.family, 10, "bold")
        ).grid(row=2, column=0, sticky="w")
        self.entry = tk.Entry(
            parent,
            bg=PANEL,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=(self.family, 18),
            highlightthickness=2,
            highlightbackground=PANEL,
            highlightcolor=ACCENT,
        )
        self.entry.grid(row=3, column=0, sticky="ew", ipady=8, pady=(4, 12))
        self.entry.bind("<Up>", self.historyPrevious)
        self.entry.bind("<Down>", self.historyNext)

        logFrame = tk.Frame(parent, bg=BG)
        logFrame.grid(row=4, column=0, sticky="nsew")
        logFrame.columnconfigure(0, weight=1)
        logFrame.rowconfigure(1, weight=1)
        tk.Label(
            logFrame, text="OUTPUT", bg=BG, fg=MUTED, font=(self.family, 10, "bold")
        ).grid(row=0, column=0, sticky="w")
        self.log = tk.Text(
            logFrame,
            bg=DISPLAY_BG,
            fg=FG,
            relief="flat",
            highlightthickness=0,
            padx=12,
            pady=8,
            font=(self.family, 11),
            state="disabled",
            wrap="word",
            height=8,
        )
        self.log.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        scroll = ttk.Scrollbar(
            logFrame,
            orient="vertical",
            command=self.log.yview,
            style="Log.Vertical.TScrollbar",
        )
        scroll.grid(row=1, column=1, sticky="ns", pady=(4, 0))
        self.log.configure(yscrollcommand=scroll.set)
        self.log.tag_configure("normal", foreground=FG)
        self.log.tag_configure("muted", foreground=MUTED)
        self.log.tag_configure("good", foreground=GOOD)
        self.log.tag_configure("warn", foreground=WARN)
        self.log.tag_configure("bad", foreground=BAD)

    def alignStack(self, event):
        position = event.width - 40
        if position > 0:
            self.stackView.configure(tabs=(position, "right"))

    def buildKeys(self, parent):
        functions = tk.Frame(parent, bg=BG)
        functions.grid(row=0, column=0, sticky="n", padx=(0, 14))
        pad = tk.Frame(parent, bg=BG)
        pad.grid(row=0, column=1, sticky="n")

        for column in range(4):
            functions.columnconfigure(column, weight=1, uniform="fn")
            pad.columnconfigure(column, weight=1, uniform="pad")

        for row, keys in enumerate(FUNCTION_KEYS):
            for column, (label, token) in enumerate(keys):
                self.button(
                    functions,
                    label,
                    lambda token=token: self.operator(token),
                    "Fn",
                    row,
                    column,
                )

        row = 0
        for keys in PREFIX_KEYS:
            for column, key in enumerate(keys):
                self.button(
                    pad, key, lambda key=key: self.append(key), "Unit", row, column
                )
            row += 1
        for keys in UNIT_KEYS:
            for column, key in enumerate(keys):
                self.button(
                    pad, key, lambda key=key: self.append(key), "Unit", row, column
                )
            row += 1

        numbers = [
            [("7", "7"), ("8", "8"), ("9", "9"), ("÷", "/")],
            [("4", "4"), ("5", "5"), ("6", "6"), ("×", "*")],
            [("1", "1"), ("2", "2"), ("3", "3"), ("−", "-")],
            [("0", "0"), (".", "."), ("±", "chs"), ("+", "+")],
        ]
        for keys in numbers:
            for column, (label, token) in enumerate(keys):
                if label in "÷×−±+":
                    self.button(
                        pad,
                        label,
                        lambda token=token: self.operator(token),
                        "Op",
                        row,
                        column,
                    )
                else:
                    self.button(
                        pad,
                        label,
                        lambda token=token: self.append(token),
                        "Num",
                        row,
                        column,
                    )
            row += 1

        self.button(pad, "⌫", self.backspace, "Clear", row, 0)
        self.button(pad, "C", self.clearOrReset, "Clear", row, 1)
        self.button(pad, "Enter", self.submit, "Enter", row, 2, columnspan=2)

    def button(self, parent, text, command, style, row, column, columnspan=1):
        def action():
            command()
            self.entry.focus_set()

        widget = ttk.Button(
            parent,
            text=text,
            command=action,
            style=f"{style}.TButton",
            takefocus=False,
            width=5,
        )
        widget.grid(
            row=row, column=column, columnspan=columnspan, sticky="nsew", padx=3, pady=3
        )
        return widget

    def append(self, text):
        self.entry.insert(tk.END, text)

    def backspace(self):
        length = len(self.entry.get())
        if length:
            self.entry.delete(length - 1, tk.END)

    def clearEntry(self):
        self.entry.delete(0, tk.END)

    def clearOrReset(self):
        if self.entry.get():
            self.clearEntry()
        else:
            self.execute("clstack")

    def submit(self):
        text = self.entry.get().strip()
        if not text:
            self.execute("dup")
            return
        self.remember(text)
        self.execute(text)

    def operator(self, token):
        text = self.entry.get().strip()
        if text:
            self.remember(text)
            self.execute(f"{text} {token}")
        else:
            self.execute(token)

    def remember(self, text):
        self.history.append(text)
        self.historyIndex = len(self.history)

    def historyPrevious(self, event):
        if self.history and self.historyIndex > 0:
            self.historyIndex -= 1
            self.setEntry(self.history[self.historyIndex])
        return "break"

    def historyNext(self, event):
        if self.historyIndex < len(self.history) - 1:
            self.historyIndex += 1
            self.setEntry(self.history[self.historyIndex])
        else:
            self.historyIndex = len(self.history)
            self.clearEntry()
        return "break"

    def setEntry(self, text):
        self.clearEntry()
        self.entry.insert(0, text)

    def execute(self, command):
        self.logLine(f"› {command}", "muted")
        try:
            result = self.calc.evaluate(self.calc.split(command))
            self.logLine(f"= {self.calc.format(result)}", "good")
        except CalculatorError as error:
            self.logLine(error.message, "bad")
            self.calc.restoreStack()
        except SystemExit:
            self.root.destroy()
            return
        except Exception as error:
            self.logLine(f"{type(error).__name__}: {error}", "bad")
            self.calc.restoreStack()
        self.clearEntry()
        self.refresh()

    def refresh(self):
        registers = self.calc.stack.stack[: self.stackRows] or [(0, "")]
        self.stackView.configure(state="normal")
        self.stackView.delete("1.0", tk.END)
        for index in reversed(range(len(registers))):
            label = self.stackLabels[index] if index < 4 else str(index)
            value = self.calc.format(registers[index])
            ending = "" if index == 0 else "\n"
            self.stackView.insert(tk.END, f"{label}:", "label")
            self.stackView.insert(
                tk.END, f"\t{value}{ending}", "top" if index == 0 else "value"
            )
        self.stackView.configure(state="disabled")
        angle = "DEG" if self.calc.trigMode == "degs" else "RAD"
        self.modeLabel.configure(text=f"{angle}   {self.calc.unit_system.upper()}")

    def logWrite(self, text, tag):
        self.log.configure(state="normal")
        self.log.insert(tk.END, text, tag)
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def logLine(self, text, tag="normal"):
        self.logWrite(text + "\n", tag)

    def printMessage(self, message="", style="line"):
        if style == "fragment":
            self.logWrite(message + " ", "normal")
        else:
            self.logWrite(message.rstrip("\n") + "\n", "normal")

    def printWarning(self, warning):
        self.logLine(f"warning: {warning.strip()}", "warn")


def main():
    root = tk.Tk()
    CalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
