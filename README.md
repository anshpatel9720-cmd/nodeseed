# EC – Engineering Calculator

A stack-based (RPN) calculator that understands SI scale factors and units (for example `10MHz`, `25mV`, `4.7kOhm`). It has a command-line mode, a desktop app and a web demo.

**▶ Try it in your browser:** https://anshpatel9720-cmd.github.io/nodeseed/

Based on [`ec`](https://github.com/KenKundert/ec) by Kenneth S. Kundert, licensed under the GNU General Public License v3 or later (see `LICENSE`).

## Project layout

```
nodeseed/
├── ec/                  the calculator package
│   ├── __init__.py
│   ├── __main__.py      lets you run "python -m ec"
│   ├── main.py          command-line program
│   ├── calculator.py    calculator engine
│   ├── actions.py       all operators, functions and constants
│   ├── gui.py           desktop app
│   └── fetch_url.py     live Bitcoin price lookup
├── docs/                web demo (served by GitHub Pages)
├── requirements.txt
└── LICENSE
```

## Setup

You need Python 3.8 or newer.

```
git clone https://github.com/anshpatel9720-cmd/nodeseed.git
cd nodeseed
pip install -r requirements.txt
```

(Optional) Use a virtual environment first:

```
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

## Command-line mode

Run these from the `nodeseed` folder.

Interactive mode (type commands at the prompt; `quit` or Ctrl+D to exit):

```
python3 -m ec
```

Calculate one expression:

```
python3 -m ec "2 3 +"
```

Run a script file (one set of commands per line):

```
python3 -m ec myscript.txt
```

Show all options:

```
python3 -m ec --help
```

## Desktop app

```
python3 -m ec.gui
```

The window uses Tkinter, which comes with Python on Windows and macOS. On Linux, install it first:

```
sudo apt install python3-tk
```

How to use it:

- Type a value (for example `10kOhm`) and press **Enter** to push it onto the stack.
- Press an operator (`+`, `×`, `sin`, `hypot`…) to apply it. If the input box has a value, that value is pushed first.
- Use the prefix and unit keys (`k`, `M`, `µ`, `V`, `Ω`, `Hz`…) to build values like `4.7kΩ`.
- You can also type full commands, such as `1MHz 2pi *`, into the input box.
- **C** clears the input box, or the whole stack if the box is already empty. **⌫** deletes one character.
- Use **↑ / ↓** to go back through earlier inputs, and **Esc** to clear the input box.

## Examples (RPN: enter the values first, then the operator)

| Input                | Result   |
|----------------------|----------|
| `2 3 +`              | `5`      |
| `100mV 25mV +`       | `125 mV` |
| `3 4 hypot`          | `5`      |
| `pi 2 *`             | `6.2832` |
| `10kOhm 10kOhm \|\|` | `5 kOhm` |
| `100 db`             | `40`     |

Useful commands: `help` (list everything), `?topic` (help on one topic), `stack` (show the stack), `vars` (show variables), `clstack` (clear the stack), `quit`.

## Web demo

The `docs/` folder runs the same Python code in the browser using [Pyodide](https://pyodide.org). GitHub Pages serves it from **Settings → Pages → Deploy from a branch → `main` / `docs`**.

Bitcoin conversions (`>$`, `>Ƀ`, `>ș`) need an internet connection in the command-line and desktop versions, and are not available in the web demo.
