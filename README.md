# EC – Engineering Calculator

A stack-based (RPN) command-line calculator that understands SI scale factors and units (for example `10MHz`, `25mV`, `4.7kOhm`).

Based on `ec` by Kenneth S. Kundert, licensed under the GNU General Public License v3 or later.

## Requirements

- Python 3.8 or newer
- pip

## Folder layout

Put the files in a folder named `ec`, next to an empty `__init__.py`:

```
project/
└── ec/
    ├── __init__.py      (empty file)
    ├── main.py
    ├── calculator.py
    ├── actions.py
    ├── fetch_url.py     (used for the Bitcoin conversions)
    └── gui.py           (desktop app)
```

## Setup

1. Open a terminal in the `project` folder (the one that contains `ec/`).

2. (Optional) Create and activate a virtual environment:

   ```
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```

3. Install the dependencies:

   ```
   pip install docopt inform quantiphy requests
   ```

## Run

Interactive mode (type commands at the prompt, `quit` or Ctrl+D to exit):

```
python3 -c "from ec.main import main; main()"
```

Run a single expression and print the result:

```
python3 -c "from ec.main import main; main()" "2 3 +"
```

Run a script file (one set of commands per line):

```
python3 -c "from ec.main import main; main()" myscript.txt
```

Show options:

```
python3 -c "from ec.main import main; main()" --help
```

## Desktop app (GUI)

Put `gui.py` in the same `ec/` folder, then from the `project` folder run:

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
- You can also type full commands such as `1MHz 2pi *` into the input box.
- **C** clears the input box, or the whole stack if the box is already empty. **⌫** deletes one character.
- Use the **↑ / ↓** keys to go back through earlier inputs, and **Esc** to clear the input box.

## Examples (RPN: enter values first, then the operator)

| Input            | Result      |
|------------------|-------------|
| `2 3 +`          | `5`         |
| `100mV 25mV +`   | `125 mV`    |
| `3 4 hypot`      | `5`         |
| `pi 2 *`         | `6.2832`    |
| `10kOhm 10kOhm \|\|` | `5 kOhm` |
| `100 db`         | `40`        |

Useful commands inside the calculator: `help` (list everything), `?topic` (help on one topic), `stack` (show the stack), `vars` (show variables), `clstack` (clear the stack), `quit`.

## Notes

- Bitcoin conversions (`>$`, `>Ƀ`, `>ș`) need an internet connection. All other features work offline.
- `fetch_url.py` must provide a `fetch_url(url, method, params)` function that returns an HTTP response with a `.json()` method.
