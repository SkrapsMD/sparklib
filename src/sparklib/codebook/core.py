from pathlib import Path

from sparklib.utils.logging.core import log
from sparklib.utils.aesthetics.palettes import LogColors as LC


def build_codebook(data, output_path=None):
    """
    Build a codebook document for a dataset.

    Parameters:
    data        - dataset to document (path or in-memory object; TBD)
    output_path - where to write the rendered codebook (TBD)

    Scaffolding only. Business logic is not yet implemented.
    """
    with log.section(f"{LC.FUNC}Codebook{LC.END}"):
        try:
            import questionary  # noqa: F401
        except ImportError:
            log(f"{LC.WARN}Install codebook extras: pip install sparklib[codebook]{LC.END}")
            return

        log(f"{LC.INFO}Codebook scaffolding is in place; generator logic is not yet implemented.{LC.END}")
        if data is not None:
            log(f"{LC.DBG}Received data: {LC.VAL}{data}{LC.END}")
        if output_path is not None:
            log(f"{LC.DBG}Target output: {LC.PATH}{Path(output_path)}{LC.END}")
        raise NotImplementedError("build_codebook is a scaffold; implementation TBD.")
