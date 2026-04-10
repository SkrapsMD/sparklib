import re


class _Section:
    def __init__(self, ctx, title):
        self.ctx=ctx
        self.title=title
    def __enter__(self):
        self.ctx(self.title)
        self.ctx.level += 1
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ctx.level -= 1

class OutputLogger:
    _instance = None

    def __new__(cls, log_file=None):
        if cls._instance is None:
            cls._instance=super().__new__(cls)
            cls._instance.level = 0
            cls._instance.indent_str = "    "
            cls._instance.log_file = None
            cls._instance.ansi_escape = re.compile(r'\033\[[0-9;]*m')
        return cls._instance

    def set_log_file(self, log_file):
        self.log_file = log_file

    def __init__(self, log_file=None):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.level = 0
        self.indent_str = "    "
        self.log_file = log_file
        self.ansi_escape = re.compile(r'\033\[[0-9;]*m')

    def __call__(self, msg):
        pfx = self.indent_str * self.level
        fmt_msg = (f"{pfx}{msg}")
        print(fmt_msg)

        if self.log_file:
            clean_msg = self.ansi_escape.sub('', fmt_msg)
            self.log_file.write(clean_msg + "\n")
            self.log_file.flush()

    def section(self, title):
        return _Section(self, title)

log = OutputLogger()
