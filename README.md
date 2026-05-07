# sparklib

Personal utility library for logging, file management, and script pipeline tooling.

---

## Table of Contents

- [Install](#install)
- [Extras](#extras)
- [Quick Import](#quick-import)
- [Logging](#logging)
  - [The `log` singleton](#the-log-singleton)
  - [`log.section()` — indented context blocks](#logsection--indented-context-blocks)
  - [`setup_log()` — file mirroring](#setup_log--file-mirroring)
  - [`LogColors` — ANSI color constants](#logcolors--ansi-color-constants)
  - [`timed` decorator](#timed-decorator)
  - [`hdr_ftr` decorator](#hdr_ftr-decorator)
- [File Management](#file-management)
  - [`check_dir()`](#check_dir)
  - [`find()`](#find)
  - [`metadata_dir()`](#metadata_dir)
  - [`archive_save()`](#archive_save)
  - [`archive_clear()`](#archive_clear)
- [Visualization Palettes](#visualization-palettes)
- [Codebook](#codebook)
- [CLI](#cli)
- [Typical Script Pattern](#typical-script-pattern)

---

## Install

```bash
pip install git+https://github.com/SkrapsMD/sparklib.git
```

---

## Extras

sparklib ships with two optional dependency groups.

| Extra | What it enables | Install command |
|---|---|---|
| `interactive` | Interactive archive selection in `archive_clear()` via `questionary` | `pip install "sparklib[interactive] @ git+https://github.com/SkrapsMD/sparklib.git"` |
| `codebook` | `build_codebook()` scaffold and `questionary` prompts (implementation TBD) | `pip install "sparklib[codebook] @ git+https://github.com/SkrapsMD/sparklib.git"` |

Neither group is required for the core logging, file management, or palette functionality.

---

## Quick Import

```python
from sparklib import log, setup_log
from sparklib import check_dir, find, metadata_dir
from sparklib import timed, hdr_ftr
from sparklib import archive_save, archive_clear
from sparklib import LogColors, LIGHT_COLOR_PALETTE, DARK_COLOR_PALETTE
from sparklib import build_codebook
```

---

## Logging

sparklib centers its output on a single global logger object called `log`. All library functions route their console output through it, which means indentation levels, color, and file mirroring apply uniformly across your entire script and any library calls made within it.

### The `log` singleton

**`log`** is an instance of `OutputLogger`, a singleton class. Only one instance ever exists for a given Python process, so every import of `log` from `sparklib` refers to the same object.

```python
from sparklib import log
```

**Calling `log` as a function**

```python
log("Processing complete.")
log(f"{LogColors.SUCC}All checks passed.{LogColors.END}")
```

`log(msg)` prints `msg` to stdout, prepended with the current indentation (`log.indent_str` repeated `log.level` times). If a log file has been set (via `setup_log()` or `log.set_log_file()`), the message is also written to the file after stripping all ANSI escape codes, ensuring the file contains plain text regardless of what color codes appear in the console output. The file is flushed after every write.

**Key attributes**

| Attribute | Type | Default | Description |
|---|---|---|---|
| `log.level` | `int` | `0` | Current indentation depth. Each level adds one `indent_str` of leading whitespace. |
| `log.indent_str` | `str` | `"    "` | The string prepended once per level. Four spaces by default. |
| `log.log_file` | file handle or `None` | `None` | The open file object that receives plain-text mirrored output. |

**`log.set_log_file(log_file)`**

Sets the file handle to mirror output to. Typically called internally by `setup_log()`, but can be called directly if you manage file handles yourself.

```python
f = open("my_log.txt", "w")
log.set_log_file(f)
log("This appears in both the console and my_log.txt.")
f.close()
```

---

### `log.section()` — indented context blocks

```python
log.section(title) -> _Section
```

Returns a `_Section` context manager. On entry it calls `log(title)` and increments `log.level` by 1. On exit it decrements `log.level` by 1. Sections can be nested arbitrarily.

```python
from sparklib import log, LogColors as LC

log("Starting data validation")

with log.section(f"{LC.FUNC}Loading files{LC.END}"):
    log(f"{LC.PATH}data/raw/survey.csv{LC.END}")
    log(f"{LC.PATH}data/raw/labels.csv{LC.END}")

    with log.section(f"{LC.INFO}Checking row counts{LC.END}"):
        log(f"{LC.VAL}survey: 4,201 rows{LC.END}")
        log(f"{LC.VAL}labels: 312 rows{LC.END}")

log("Validation complete")
```

Console output (colors omitted for clarity):

```
Starting data validation
Loading files
    data/raw/survey.csv
    data/raw/labels.csv
    Checking row counts
        survey: 4,201 rows
        labels: 312 rows
Validation complete
```

`log.section()` does not suppress exceptions — if the body raises, `log.level` is still decremented on exit before the exception propagates.

---

### `setup_log()` — file mirroring

```python
setup_log(log_dir, log_name) -> file handle
```

Creates a new timestamped log file and points the global `log` singleton at it, so every subsequent `log()` call writes to both the console and the file.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `log_dir` | `Path` or `str` | Directory in which the log file will be created. Created if it does not exist. |
| `log_name` | `str` | Base name for the log file. A `.log` extension is added automatically if none is present. |

**Behavior, step by step**

1. If `log_name` has no file extension, `.log` is appended.
2. `archive_save(log_dir, log_name)` is called internally, which moves any existing timestamped log files matching the same stem into `log_dir/archive/<stem>/` and returns a fresh timestamped path.
3. The new log file is opened in write mode (`'w'`).
4. `log.set_log_file()` is called with the open file handle, activating file mirroring for all subsequent `log()` calls.
5. Colored setup messages are printed to the console.
6. The open file handle is returned. **The caller is responsible for closing it.**

**Return value**

An open, writable file handle. Close it when your script finishes.

```python
from pathlib import Path
from sparklib import setup_log, log

LOGS = Path("results/logs")

log_file = setup_log(LOGS, log_name="my_script")

log("Script started.")
# ... your code ...
log("Script finished.")

log_file.close()
```

The file created will be named something like `results/logs/my_script_20260507_143022.log`. Any prior file named `my_script_<timestamp>.log` in that directory is rotated into `results/logs/archive/my_script/` before the new one is opened.

---

### `LogColors` — ANSI color constants

```python
from sparklib import LogColors
```

`LogColors` is a plain class whose attributes are ANSI escape sequences. There are no instances — use the class attributes directly.

| Attribute | ANSI code | Color | Intended use |
|---|---|---|---|
| `LogColors.PATH` | `\033[96m` | Cyan | File and directory paths |
| `LogColors.FUNC` | `\033[1;95m` | Bold Magenta | Function entry points, section headers |
| `LogColors.SUCC` | `\033[92m` | Green | Successful operations |
| `LogColors.WARN` | `\033[93m` | Yellow | Warnings and caution messages |
| `LogColors.FAIL` | `\033[1;91m` | Bright Red | Errors and failures |
| `LogColors.VAL` | `\033[94m` | Blue | Output values and numeric results |
| `LogColors.INFO` | `\033[97m` | Bright White | General informational text |
| `LogColors.METR` | `\033[36m` | Dark Cyan | Metrics and statistics |
| `LogColors.DBG` | `\033[90m` | Dark Gray | Debug messages |
| `LogColors.END` | `\033[0m` | — | Resets all formatting — always close a color with this |
| `LogColors.BOLD` | `\033[1m` | — | Bold text |
| `LogColors.UL` | `\033[4m` | — | Underlined text |

**Every color sequence must be closed with `LogColors.END`.** Without it, the color bleeds into all subsequent output.

```python
from sparklib import log, LogColors as LC

log(f"{LC.FUNC}=== Section: Load Data ==={LC.END}")
log(f"Reading {LC.PATH}/data/raw/survey.csv{LC.END}")
log(f"Rows loaded: {LC.VAL}4,201{LC.END}")
log(f"{LC.WARN}Warning: 3 rows had missing IDs{LC.END}")
log(f"{LC.SUCC}Load complete.{LC.END}")
```

When `log` writes to a file (via `setup_log()`), all ANSI codes are stripped automatically — the file always contains plain text.

---

### `timed` decorator

```python
from sparklib import timed

@timed
def my_function():
    ...
```

Wraps a function with a 60-character-wide timing bar printed before and after execution.

**Before the function runs**, prints:

```
=================== Start: 14:30:22 ===================
```

**After the function returns**, prints:

```
============= End: 14:30:25 | Duration: 3.14s ==========
```

- Wall-clock times are formatted as `HH:MM:SS` using `time.strftime()`.
- Elapsed time uses `time.perf_counter()` and is reported in seconds with two decimal places.
- Output goes through the global `log`, so it is subject to current indentation level and file mirroring.
- `@timed` preserves the wrapped function's name and docstring via `functools.wraps`.

`timed` is commonly stacked with `hdr_ftr`. When stacking, put `@hdr_ftr` on top (outermost) and `@timed` directly above the function definition:

```python
@hdr_ftr("my_script", "Processes the quarterly survey data.")
@timed
def main():
    ...
```

---

### `hdr_ftr` decorator

```python
from sparklib import hdr_ftr

@hdr_ftr(script_name, script_description)
def main():
    ...
```

A decorator factory. Call it with two strings to get a decorator, then apply that decorator to a function.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `script_name` | `str` | The script's identifier, typically its filename stem without `.py`. |
| `script_description` | `str` | A one-line description of what the script does. |

**Behavior**

Before the function runs, logs (in color):

```
STARTING CODE:  my_script.py
Processes the quarterly survey data.
```

After the function returns, logs:

```
ENDING CODE:  my_script.py
```

Output goes through the global `log`. The decorator preserves the wrapped function's name and docstring via `functools.wraps`.

**Example**

```python
from sparklib import hdr_ftr, timed, log

SCRIPT_NAME = "02_clean"
SCRIPT_DESCRIPTION = "Cleans raw survey responses and produces an intermediate file."

@hdr_ftr(SCRIPT_NAME, SCRIPT_DESCRIPTION)
@timed
def main():
    log("Dropping duplicates...")
    log("Standardizing column names...")

main()
```

---

## File Management

### `check_dir()`

```python
check_dir(dir_paths) -> None
```

Verifies that each path in `dir_paths` exists. Creates missing directories (including all intermediate parents) using `mkdir(parents=True)`. Reports each result through `log`.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `dir_paths` | `list[Path]` or `str` | A list of `Path` objects to check. If a single string is passed, it is automatically wrapped in a list. |

**Behavior**

- Iterates over each path, logging under nested `log.section()` blocks.
- If the path does not exist: creates it and logs a warning (`DIRECTORY MISSING: Creating directory`).
- If the path exists: logs a success message (`DIRECTORY EXISTS`).
- Returns `None`.

```python
from pathlib import Path
from sparklib import check_dir

RAW   = Path("data/raw")
INT   = Path("data/int")
FINAL = Path("data/final")
LOGS  = Path("results/logs")
FIGS  = Path("results/figs")

check_dir([RAW, INT, FINAL, LOGS, FIGS])
```

Console output (colors omitted):

```
Checking existence of 5 directories...
Directory Validation
    Checking data/raw...
        DIRECTORY EXISTS
    Checking data/int...
        DIRECTORY MISSING: Creating directory
    Checking data/final...
        DIRECTORY MISSING: Creating directory
    ...
```

---

### `find()`

```python
find(path, target_name) -> Path | None
```

Searches for a file or directory named `target_name` within `path` using breadth-first search.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `path` | `Path` | The root directory to search from. |
| `target_name` | `str` | Exact name (not a glob) of the file or directory to find. |

**Behavior**

- Uses BFS, so shallower matches are returned before deeper ones.
- Skips any directory whose name starts with `.` (hidden directories). The contents of hidden directories are not searched.
- Returns the `Path` of the first match (file or directory), or `None` if nothing is found.

```python
from pathlib import Path
from sparklib import find

root = Path("/home/user/project")

code_dir = find(root, "code")
if code_dir:
    print(f"Found: {code_dir}")
else:
    print("Not found.")
```

---

### `metadata_dir()`

```python
metadata_dir(path) -> dict
```

Scans all `.py` files in `path` (non-recursive, one level only) and extracts metadata from each file's preamble.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `path` | `Path` or `str` | Directory containing the `.py` script files to scan. |

**Script naming convention**

Each file must begin with a script number prefix separated from the rest of the name by an underscore. Recognized prefix formats:

- Numeric with optional letter suffix: `01_`, `01a_`, `04b_`
- Single letter: `a_`, `b_`

Files whose names do not match this pattern are skipped with a warning.

**Preamble variables**

The function reads `SCRIPT_NAME` and `SCRIPT_DESCRIPTION` from each file's text using regex. These must be module-level string assignments:

```python
SCRIPT_NAME = "cleaning"
SCRIPT_DESCRIPTION = "Cleans and standardizes raw survey responses."
```

If `SCRIPT_NAME` is not found, the function falls back to the portion of the filename after the first `_`. If `SCRIPT_DESCRIPTION` is not found, the description is left as an empty string.

**Sorting**

Results are sorted by script number: numeric prefixes sort first (by integer value, then by any letter suffix), followed by pure-letter prefixes alphabetically. For example: `01`, `01a`, `02`, `04b`, `a`, `b`.

**Output**

Prints a formatted table via `log`:

```
==================================================
Script Metadata for: /path/to/scripts
==================================================
  01 | cleaning             | Cleans raw survey responses.
 01a | cleaning_alt         | Alternative merge approach.
  02 | merge                | Merges cleaned files.
==================================================
```

**Return value**

A `dict` mapping each script number string to a dict with `"name"` and `"description"` keys:

```python
{
    "01":  {"name": "cleaning",      "description": "Cleans raw survey responses."},
    "01a": {"name": "cleaning_alt",  "description": "Alternative merge approach."},
    "02":  {"name": "merge",         "description": "Merges cleaned files."},
}
```

```python
from pathlib import Path
from sparklib import metadata_dir

meta = metadata_dir(Path("code"))
for num, info in meta.items():
    print(f"{num}: {info['name']}")
```

---

### `archive_save()`

```python
archive_save(obj_dir, obj_name) -> Path
```

Prepares a versioned save path for a file. Rotates any existing timestamped versions of the same file into an archive subdirectory and returns a new path for the next version. **It does not create the file itself** — only the path is returned.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `obj_dir` | `Path` or `str` | Directory where the file lives (or will live). Created if it does not exist. |
| `obj_name` | `str` | File name including extension, e.g. `"my_report.pdf"` or `"survey_clean.csv"`. |

**Behavior, step by step**

1. Creates `obj_dir` if it does not exist.
2. Derives `stem` and `suffix` from `obj_name`.
3. Scans `obj_dir` for any existing files matching `{stem}_*{suffix}` (prior timestamped versions).
4. Moves all matching files to `obj_dir/archive/{stem}/`.
5. Constructs and returns a new path: `obj_dir/{stem}_{YYYYMMDD_HHMMSS}{suffix}`.

The returned path can be passed directly to any function that writes a file.

```python
from pathlib import Path
from sparklib import archive_save
import matplotlib.pyplot as plt

FIGS = Path("results/figs")

# First run: returns results/figs/chart_20260507_143022.png
fig_path = archive_save(FIGS, "chart.png")
plt.savefig(fig_path)

# Second run: the previous file is moved to results/figs/archive/chart/
# and a new path is returned.
fig_path = archive_save(FIGS, "chart.png")
plt.savefig(fig_path)
```

`archive_save()` is also used internally by `setup_log()` to rotate old log files before opening a new one.

---

### `archive_clear()`

```python
archive_clear(target_dir, clear_all=False, confirm=True) -> int
```

Deletes files from the `archive/` subdirectory inside `target_dir`.

**Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `target_dir` | `Path` or `str` | — | The directory that contains an `archive/` subdirectory. |
| `clear_all` | `bool` | `False` | If `True`, all archived files across all subdirectories are deleted without prompting for selection. If `False`, an interactive checkbox prompt is shown (requires `sparklib[interactive]`). |
| `confirm` | `bool` | `True` | If `True`, prints the count of files to be deleted and prompts `Proceed? [Y/N]` before deleting. Set to `False` to skip the prompt. |

**Behavior**

1. Looks for `target_dir/archive/`. If it does not exist, logs a message and returns `0`.
2. Discovers archive subdirectories (one per archived stem, e.g. `archive/my_script/`).
3. **If `clear_all=True`**: all subdirectories are targeted for deletion.
4. **If `clear_all=False`**: launches an interactive `questionary` checkbox listing each subdirectory with its file count, plus "CLEAR NONE" and "CLEAR ALL" options. If `questionary` is not installed, logs a warning and returns `0`. Pressing Escape or selecting nothing cancels without deleting anything.
5. **If `confirm=True`**: prints the number of files to be deleted and prompts `Proceed? [Y/N]`. Any response other than `y` cancels.
6. Deletes each selected file and removes any subdirectory that is empty afterward.
7. Returns the count of deleted files.

```python
from pathlib import Path
from sparklib import archive_clear

LOGS = Path("results/logs")

# Non-interactive: delete all archived logs without a Y/N prompt
deleted = archive_clear(LOGS, clear_all=True, confirm=False)
print(f"Deleted {deleted} files.")

# Interactive: show a checkbox menu, ask for confirmation before deleting
deleted = archive_clear(LOGS, clear_all=False, confirm=True)
```

The interactive checkbox (when `clear_all=False`) looks like:

```
Select archive directories to clear (↑↓ navigate, Space toggle, Enter confirm, Esc cancel):
? Clear which archives?
 > [ ] CLEAR NONE (CONTINUE)
   [ ] my_script (3 files)
   [ ] other_script (1 file)
   [ ] CLEAR ALL
```

---

## Visualization Palettes

```python
from sparklib import LIGHT_COLOR_PALETTE, DARK_COLOR_PALETTE
```

Two lists of hex color strings for use with matplotlib or any other visualization library.

**`LIGHT_COLOR_PALETTE`** — 10 colors, suitable for light backgrounds:

```python
["#3581b4", "#ca590f", "#d34682", "#56bfd6", "#f3bb00",
 "#4a3e8e", "#53c49f", "#580d10", "#006278", "#385100"]
```

**`DARK_COLOR_PALETTE`** — 8 colors, suitable for dark backgrounds:

```python
["#6da4c9", "#f08033", "#e17fa9", "#9f97d2",
 "#53c49f", "#d66d73", "#ddaa00", "#80cfe0"]
```

```python
import matplotlib.pyplot as plt
from sparklib import LIGHT_COLOR_PALETTE

fig, ax = plt.subplots()
for i, color in enumerate(LIGHT_COLOR_PALETTE):
    ax.bar(i, 1, color=color)
plt.show()
```

---

## Codebook

```python
from sparklib import build_codebook
```

**`build_codebook(data, output_path=None)`**

Scaffold entry point for generating a codebook document from a dataset. Requires `sparklib[codebook]`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | any | — | The dataset to document. Exact type is TBD. |
| `output_path` | `str` or `None` | `None` | Path to write the rendered codebook to. TBD. |

**Current status**: This function always raises `NotImplementedError`. The scaffolding is in place and the function can be imported, but the business logic has not yet been implemented.

```python
from sparklib import build_codebook

# This will raise NotImplementedError
build_codebook(my_dataframe, output_path="results/codebook/codebook.tex")
```

---

## CLI

sparklib installs a `sparklib` command-line entry point.

### `sparklib metadata <path>`

```bash
sparklib metadata <path>
```

Runs `metadata_dir()` on the given path and prints the formatted metadata table to the console.

If `<path>` does not exist as given, the CLI searches for a directory with that name from the current working directory using BFS (the same logic as `find()`).

```bash
# Absolute path
sparklib metadata /home/user/project/code

# Directory name — found via BFS from cwd
sparklib metadata code
```

### `sparklib codebook <data> [-o output]`

```bash
sparklib codebook <data> [-o output]
```

Calls `build_codebook()` on the given data path. Currently raises `NotImplementedError` as the implementation is not yet complete.

| Argument | Description |
|---|---|
| `<data>` | Path to the dataset to document. |
| `-o`, `--output` | Optional output path for the rendered codebook. |

```bash
sparklib codebook data/raw/survey.dta -o results/codebook/codebook.tex
```

---

## Typical Script Pattern

The following pattern illustrates how the logging, timing, and directory-management tools compose into a complete script workflow.

```python
from pathlib import Path
from sparklib import hdr_ftr, timed, check_dir, setup_log, archive_clear, log, LogColors as LC

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW   = PROJECT_ROOT / "data" / "raw"
INT   = PROJECT_ROOT / "data" / "int"
FINAL = PROJECT_ROOT / "data" / "final"
LOGS  = PROJECT_ROOT / "results" / "logs"
FIGS  = PROJECT_ROOT / "results" / "figs"

SCRIPT_NAME        = "02_merge"
SCRIPT_DESCRIPTION = "Merges cleaned survey files into a single analysis dataset."

@hdr_ftr(SCRIPT_NAME, SCRIPT_DESCRIPTION)
@timed
def main():
    check_dir([RAW, INT, FINAL, LOGS, FIGS])
    archive_clear(LOGS, clear_all=False, confirm=False)

    with log.section(f"{LC.FUNC}Loading data{LC.END}"):
        log(f"Reading {LC.PATH}{RAW / 'survey.csv'}{LC.END}")
        # ... load data ...

    with log.section(f"{LC.FUNC}Merging{LC.END}"):
        log(f"{LC.INFO}Merging on respondent_id{LC.END}")
        # ... merge ...
        log(f"{LC.SUCC}Merge complete: {LC.VAL}4,201 rows{LC.END}")

if __name__ == "__main__":
    log_file = setup_log(LOGS, log_name=SCRIPT_NAME)
    main()
    log_file.close()
```

**What this produces at runtime:**

1. `setup_log()` rotates any prior `02_merge_<timestamp>.log` into `results/logs/archive/02_merge/` and opens a new timestamped log file.
2. `@hdr_ftr` prints a colored "STARTING CODE: 02_merge.py" header and description.
3. `@timed` prints a start-time bar with the current wall clock time.
4. `check_dir()` validates all listed directories, creating any that are missing, and logs each result.
5. `archive_clear()` presents an interactive checkbox to clean up old archived logs (or skips it since `confirm=False` still shows the menu when `clear_all=False`; pass `clear_all=True, confirm=False` to delete silently).
6. All `log()` calls inside `main()` are indented correctly by `log.section()` context, colored on the console, and written as plain text to the log file.
7. `@timed` prints an end-time bar with elapsed seconds.
8. `@hdr_ftr` prints "ENDING CODE: 02_merge.py".
9. The log file is closed.

To generate a metadata table for the script directory afterward:

```bash
sparklib metadata code
```
