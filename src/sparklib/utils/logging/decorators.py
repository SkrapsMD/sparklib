import functools
import time
from textwrap import dedent

from sparklib.utils.aesthetics.palettes import LogColors as LC
from .core import log

def hdr_ftr(script_name, script_description):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log(dedent(f"""\
            {LC.FUNC}STARTING CODE: {LC.INFO} {script_name}.py{LC.END}
            {LC.INFO}{script_description}{LC.END}"""))
            result = func(*args, **kwargs)
            log(dedent(f"""\
            {LC.FUNC}ENDING CODE:{LC.INFO} {script_name}.py{LC.END}"""))
            return result
        return wrapper
    return decorator

def timed(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        bar_width = 60
        start_wall = time.strftime('%H:%M:%S')
        start_str = f" Start: {start_wall} "
        pad = bar_width - len(start_str)
        left = pad // 2
        right = pad - left
        log(f"{'=' * left}{start_str}{'=' * right}")
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        end_wall = time.strftime('%H:%M:%S')
        end_str = f" End: {end_wall} | Duration: {elapsed:.2f}s "
        pad = bar_width - len(end_str)
        left = pad // 2
        right = pad - left
        log(f"{'=' * left}{end_str}{'=' * right}")
        return result
    return wrapper
