"""
This module provides aesthetic utilities for the Parquet-Parrot project.
These utilities include:
    - Output / Log context management (e.g. indentations)
    - Color specifications for console logging
    - Color specifications for visualizations (default color palette)
    - Font specifications for visualizations (default font family and size, able to be edited by user)
"""
# Console Output Colors
class LogColors:
    # Functional semantics
    PATH = '\033[96m'       # Cyan - file/directory paths
    FUNC =  '\033[1;95m'    # Magenta - function entry/section headers
    SUCC = '\033[92m'       # Green - successful operations
    WARN = '\033[93m'       # Yellow - warnings/caution
    FAIL = '\033[1;91m'     # Bright red - errors/failures
    VAL = '\033[94m'        # Blue - output values/numbers
    INFO = '\033[97m'       # Bright white - general information
    METR = '\033[36m'       # Dark cyan - metrics/statistics
    DBG = '\033[90m'        # Dark gray - debug messages
    END = '\033[0m'         # Reset
    BOLD = '\033[1m'        # Bold text
    UL = '\033[4m'          # Underlined text

# Default Color Palette for Visualizations
LIGHT_COLOR_PALETTE = ["#3581b4", "#ca590f", "#d34682", "#56bfd6", "#f3bb00","#4a3e8e", "#53c49f", "#580d10", "#006278", "#385100" ]
DARK_COLOR_PALETTE = ["#6da4c9","#f08033", "#e17fa9", "#9f97d2",  "#53c49f", "#d66d73", "#ddaa00", "#80cfe0"]

