import shutil
from datetime import datetime
from pathlib import Path

from sparklib.utils.logging.core import log
from sparklib.utils.aesthetics.palettes import LogColors as LC

def archive_save(obj_dir, obj_name):
    """
    Parameters:
    obj_dir - directory the object is to be saved to
    obj_name - object name
    """
    obj_dir = Path(obj_dir)
    obj_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(obj_name).stem
    suffix = Path(obj_name).suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    new_obj_name = f"{stem}_{timestamp}{suffix}"
    new_obj_path = obj_dir / new_obj_name

    archive_dir = obj_dir / "archive" / stem
    archive_dir.mkdir(parents=True, exist_ok=True)
    existing_obj = list(obj_dir.glob(f"{stem}_*{suffix}"))

    if existing_obj:
        archive_dir.mkdir(parents=True, exist_ok=True)

        for old_obj in existing_obj:
            archive_path = archive_dir / old_obj.name
            shutil.move(str(old_obj), str(archive_path))

    return new_obj_path


def archive_clear(target_dir, clear_all=False, confirm=True):
    """
    Clear archived files within a directory's archive subdirectory.

    Parameters:
    target_dir  - directory containing an 'archive' subdirectory
    clear_all   - If True, clears all archives. If False, interactive selection.
    confirm     - If True, prompts for confirmation before deletion.

    Returns: number of files deleted
    """
    target_dir = Path(target_dir)
    archive_dir = target_dir / "archive"

    CLEAR_NONE = "__clear_none__"
    CLEAR_ALL = "__clear_all__"

    with log.section(f"{LC.FUNC}Clear Archives{LC.END}"):
        log(f"{LC.DBG}Attempting to find {LC.PATH}{archive_dir.relative_to(Path.cwd())}{LC.END}")
        if not archive_dir.exists():
            log(f"{LC.INFO}No archive directory found. Nothing to clear.{LC.END}")
            return 0

        # Discover available archive subdirectories
        available_dirs = sorted([d for d in archive_dir.iterdir() if d.is_dir()], key=lambda d: d.name)

        if not available_dirs:
            log(f"{LC.INFO}No archived directories found.{LC.END}")
            return 0

        # Determine what to delete
        if clear_all:
            target_dirs = available_dirs
            desc = "all archives"
        else:
            # Interactive selection
            try:
                import questionary
            except ImportError:
                log(f"{LC.WARN}Install 'questionary' for interactive selection: pip install questionary{LC.END}")
                return 0

            choices = [
                questionary.Choice(title="CLEAR NONE (CONTINUE)", value=CLEAR_NONE)
            ]
            for d in available_dirs:
                file_count = len(list(d.iterdir()))
                label = f"{d.name} ({file_count} file{'s' if file_count != 1 else ''})"
                choices.append(questionary.Choice(title=label, value=d))
            choices.append(questionary.Choice(title="CLEAR ALL", value=CLEAR_ALL))

            log(f"{LC.INFO}Select archive directories to clear ({LC.UL}↑↓{LC.END}{LC.INFO} navigate, {LC.UL}Space{LC.END}{LC.INFO} toggle, {LC.UL}Enter{LC.END}{LC.INFO} confirm, {LC.UL}Esc{LC.END}{LC.INFO} cancel):{LC.END}")
            selected = questionary.checkbox(
                "Clear which archives?",
                choices=choices,
            ).ask()

            if selected is None:
                log(f"{LC.INFO}Escaped. Cancelled.{LC.END}")
                return 0

            if len(selected) == 0:
                log(f"{LC.INFO}Nothing selected. Cancelled.{LC.END}")
                return 0

            if CLEAR_NONE in selected:
                log(f"{LC.INFO}Clear none selected. No action taken.{LC.END}")
                return 0

            if CLEAR_ALL in selected:
                target_dirs = available_dirs
                desc = "all archives"
            else:
                target_dirs = selected
                names = ", ".join(d.name for d in target_dirs)
                desc = f"selected archives ({names})"

        # Collect files to delete
        files_to_delete = []
        for d in target_dirs:
            if d.exists():
                files_to_delete.extend(f for f in d.iterdir() if f.is_file())

        if not files_to_delete:
            log(f"{LC.INFO}No archived files found for {desc}.{LC.END}")
            return 0

        # Confirm deletion
        log(f"{LC.WARN}About to delete {LC.VAL}{len(files_to_delete)}{LC.END} archived file(s) for {desc}")
        if confirm:
            response = input(f"Proceed? [Y/N]: ").strip().lower()
            if response != 'y':
                log(f"{LC.INFO}Cancelled.{LC.END}")
                return 0

        # Delete files
        with log.section(f"{LC.INFO}Deleting files{LC.END}"):
            deleted = 0
            for file in files_to_delete:
                file.unlink()
                deleted += 1
                log(f"{LC.DBG}Deleted {LC.PATH}{file.name}{LC.END}")

        # Remove empty directories
        for d in target_dirs:
            if d.exists() and not list(d.iterdir()):
                d.rmdir()
                log(f"{LC.DBG}Removed empty directory {LC.PATH}{d.name}{LC.END}")

        log(f"{LC.SUCC} - Deleted {LC.VAL}{deleted}{LC.END} archived file(s){LC.END}")
        return deleted

