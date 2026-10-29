from dataclasses import dataclass, replace


@dataclass(frozen=True)
class LogType:
    name: str
    # general config
    to_file: bool = True
    to_console: bool = True
    ignore_closed_console: bool = False
    # specjal inputs
    newline_formatting: bool = True

    def __call__(self, **changes):
        return replace(self, **changes)