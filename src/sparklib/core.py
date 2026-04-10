""" This is the main wrapper where any joint convenience functions are to be found.

* setup_logs
    - pulls from the log in utils.logging, and the archive handling in utils.management.
"""

from pathlib import Path

from .utils.aesthetics.palettes import LogColors as LC
from .utils.logging.core import log
from .utils.management.archive import archive_save

#─ SETUP LOGS ─────────────────────────────────────────#

def setup_log(log_dir, log_name):
    print(f"{LC.DBG}{'='*60}{LC.END}")
    print(f"{LC.DBG}Logging: ```setup_log'''")

    if not Path(log_name).suffix:
        log_name = f"{log_name}.log"
    new_log_path = archive_save(log_dir, log_name)

    print(f"{LC.SUCC}   - Creating Log File: {LC.PATH}{new_log_path.relative_to(Path.cwd())}{LC.END}")
    print(f"{LC.DBG}{'='*60}{LC.END}")
    log_file = open(new_log_path, 'w')
    log.set_log_file(log_file)

    return log_file

