# sparklib

Personal utility library for logging, file management, and script pipeline tooling.

## Install

```bash
pip install git+https://github.com/SkrapsMD/sparklib.git
```

For interactive archive selection:

```bash
pip install "sparklib[interactive] @ git+https://github.com/SkrapsMD/sparklib.git"
```

## Usage

```python
from sparklib import log, setup_log, check_dir, find, timed, hdr_ftr
from sparklib import archive_save, archive_clear
from sparklib import LogColors, LIGHT_COLOR_PALETTE, DARK_COLOR_PALETTE
```
