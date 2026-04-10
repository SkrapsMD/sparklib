"""
Core File Management.

- check_dir(dirs)
    * Does each dir of dirs exist?
        Y - continue
        N - create dir of dirs
    * Report whether they exist or not.

- find(obj: dir|file)
    * 1) assume dir, try and find dir
    * 2) if not dir, try and find file

- graph_dirs(output_path)
    * create figure depicting the file path structure.

- metadata_dir(path)
    * scans a directory of .py files, extracts the script number from the
      filename prefix (before the first '_'), and reads SCRIPT_NAME and
      SCRIPT_DESCRIPTION from preamble variables.

"""

import re
from collections import deque
from pathlib import Path

from ..logging.core import log
from ..aesthetics.palettes import LogColors as LC


def check_dir(dir_paths):
    """
    Check existence of directories. Create if otherwise.

    :param dir_paths: List of directory paths to check (or single directory path as a string).
    :type dir_paths: list
    """
    if isinstance(dir_paths, str):
        dir_paths = [dir_paths]
        log(f"{LC.DBG}Received single directory path as string. Processing as list: {dir_paths}{LC.END}")

    log(f"{LC.INFO}Checking existence of {LC.VAL}{len(dir_paths)}{LC.END} directories...")
    cwd = Path.cwd()
    with log.section(f"{LC.FUNC}Directory Validation{LC.END}"):
        for dir_path in dir_paths:
            try:
                disp_path = dir_path.relative_to(cwd)
            except ValueError:
                disp_path = dir_path
            with log.section(f"Checking {LC.PATH}{disp_path}{LC.END}..."):
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    log(f"{LC.WARN}DIRECTORY MISSING: Creating directory{LC.END}")
                else:
                    log(f"{LC.SUCC}DIRECTORY EXISTS{LC.END}")
    return None


def find(path, target_name):
    """
    Search for a specific directory with the specified name within the given path
    using a breadth first approach to search through all subdirectories.
    """
    queue = deque([path])
    while queue:
        current = queue.popleft()
        for d in current.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                if d.name == target_name:
                    return d
                queue.append(d)
            elif d.is_file() and d.name == target_name:
                return d
    return None

def graph_dir(path, output_path, omit=None):
    """
    Create visualization for the project folder.

    path - path to begin the visualization from,
    output_path - path to output the visual to,
    omit - folders/files to omit. Takes a list. "*" wildcards.
    """
    pass

def metadata_dir(path):
    """
    Obtains metadata for all python (for now) scripts in the folder 'path'

    Defaults to trying to find 'code', or '.py' files

    Does not dig down, only does the main routines of the program --
    """

    def metadata_file(file_path):
        """
        Obtains metadata for a particular python script at file_path.

        Extracts script_number from the filename prefix (before the first '_').
        Reads SCRIPT_NAME and SCRIPT_DESCRIPTION from preamble variables.

        Returns a dict with script_number, script_name, script_description
        or None if no number could be extracted from the filename.
        """
        # Extract script number from filename prefix (e.g. '01a' from '01a_cleaning.py')
        stem = file_path.stem
        parts = stem.split("_", 1)
        prefix = parts[0]

        # Validate prefix looks like a script number (numeric, alpha, or mix like '01a')
        if not re.match(r'^(\d+[a-zA-Z]*|[a-zA-Z])$', prefix):
            log(f"  WARNING: Could not extract script number from '{file_path.name}' -- skipping")
            # TODO: prompt the user to manually label the ordering for this file
            return None

        text = file_path.read_text()

        patterns = {
            "script_name": re.compile(r"""^SCRIPT_NAME\s*=\s*['"](.+?)['"]\s*$""", re.MULTILINE | re.IGNORECASE),
            "script_description": re.compile(r"""^SCRIPT_DESCRIPTION\s*=\s*['"](.+?)['"]\s*$""", re.MULTILINE | re.IGNORECASE),
        }

        result = {"script_number": prefix}
        for key, pattern in patterns.items():
            match = pattern.search(text)
            if match:
                result[key] = match.group(1)

        return result

    def sort_key(key):
        """
        Sort numeric keys ('04', '04a') and alpha keys ('a', 'b') naturally.
        Numeric keys sort first by int then suffix: '04' < '04a' < '05'.
        Pure alpha keys sort after all numeric keys alphabetically.
        """
        match = re.match(r'^(\d+)([a-zA-Z]*)$', key)
        if match:
            return (0, int(match.group(1)), match.group(2))
        return (1, 0, key)

    path = Path(path)
    metadata = {}

    for py_file in sorted(path.glob("*.py")):
        result = metadata_file(py_file)
        if result:
            num = result["script_number"]
            # Fall back to the rest of the filename if SCRIPT_NAME not set
            fallback_name = py_file.stem.split("_", 1)[1] if "_" in py_file.stem else ""
            metadata[num] = {
                "name": result.get("script_name", fallback_name),
                "description": result.get("script_description", ""),
            }

    metadata = dict(sorted(metadata.items(), key=lambda item: sort_key(item[0])))

    log(f"{'='*50}")
    log(f"Script Metadata for: {path}")
    log(f"{'='*50}")
    for num, info in metadata.items():
        log(f"  {num:>4s} | {info['name']:<20s} | {info['description']}")
    log(f"{'='*50}")

    return metadata
