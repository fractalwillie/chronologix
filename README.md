# Chronologix

Chronologix is a fully asynchronous, modular logging system for Python.

It writes structured log files across multiple named sinks, supports time-based chunking, and avoids the standard logging module completely.

---

## Features

-  Fully async logging 
-  Time-based rollover (e.g. every `24h`, `1h`, `15m`)
-  Multiple independent log sinks with custom filters
-  Optional mirror sink that records everything above set threshold
-  Log level filtering per sink (`DEBUG`, `ERROR`, etc.)
-  Safe file I/O with atomic disk writes
-  Config validation with clear error feedback
-  Custom log paths via `str` or `pathlib.Path`
-  Predictable file and folder structure for automated processing
-  No logging module, no global state

---

## Installation

Chronologix requires **Python 3.7+**.
```bash
pip install chronologix
```

---

## Usage example

```python
import asyncio
from chronologix import LogConfig, LogManager

config = LogConfig(
    base_log_dir="my_logs",
    interval="1h",  # rollover every hour
    sinks={
        "app": {"file": "app.log", "min_level": "INFO"},
        "errors": {"file": "errors.log", "min_level": "ERROR"},
    },
    mirror={
        "file": "audit.log",  # captures all messages regardless of sink
        "min_level": "NOTSET" # min_level for mirror is optional, defaults to NOTSET without it
    },
    timestamp_format="%H:%M:%S.%f"
)

logger = LogManager(config)

async def divide(a, b):
    try:
        result = a / b
        await logger.log(f"Division result: {result}", level="INFO")  # level passed as argument, goes to app + mirror
    except Exception as e:
        await logger.error(f"Exception occurred: {e}")  # wrapper method - .error normalized to ERROR min_level, goes to errors + app + mirror

# showcase of several different methods of logging
async def main():
    await logger.start() # needs to be called before any logging happens
    await logger.log("Some NOTSET level msg")  # defaults to NOTSET, goes to mirror only
    await logger.debug("Some DEBUG level msg")  # goes to mirror only (app min_level = INFO)
    await logger.info("Some INFO level msg")  # app + mirror
    await logger.warning("Some WARNING level msg")  # app + mirror
    await logger.error("Some ERROR level msg")  # errors + app + mirror
    await logger.CRITICAL("Some CRITICAL level msg")  # errors + app + mirror (upper/lowercase doesn't matter, they're normalized before processing)
    await divide(10, 0)  # triggers zero division error → errors + mirror
    await logger.stop()


```
This example will produce following:
- Two new folder per hour like: 2025-05-04__14-00/ and 2025-05-04__15-00/
- Three log files inside each: app.log (INFO and above), errors.log (ERROR and above), audit.log (NOTSET)
- The exception will be logged to both sinks and mirror
- Messages without level (like "Some NOTSET level msg") will be treated as NOTSET and only land in sinks that accept that level (here: audit.log mirror file)
- Level filtering and routing is automatic. You don’t specify a target sink, only a level (or nothing)

---

## Path structure

You can set the log output directory using either a string path or a `pathlib.Path` object.

Examples:
```python
LogConfig(base_log_dir="logs")  # relative to current working dir
LogConfig(base_log_dir="/var/log/chronologix")  # absolute path (Linux)
LogConfig(base_log_dir=Path("~/.chronologix").expanduser())  # user home dir
```
Chronologix will create any missing directories automatically.

---

## Intervals

The `interval` controls how frequently Chronologix creates a new folder and rotates the log files.

Supported values:
- `"24h"`
- `"12h"`
- `"6h"`
- `"3h"`
- `"1h"`
- `"30m"`
- `"15m"`
- `"5m"`

Each interval corresponds to a different granularity of time-based chunking:
- `interval="24h"` → folders like `2025-05-04/` → `2025-05-05/`
- `interval="1h"` → folders like `2025-05-04__14-00/` → `2025-05-04__15-00/`

---

## Sinks

Each sink is defined by:
- a `file` name (relative to the chunk folder)
- a `min_level` that controls what gets written

Example:
```python
sinks={
    "debug":  {"file": "debug.log", "min_level": "NOTSET"},
    "alerts": {"file": "alerts.log", "min_level": "CRITICAL"},
}
```
A single message may be written to multiple sinks if its level qualifies.
You can define as many sinks as needed or just a single one.

---

## Mirroring

You can configure an optional mirror file to capture all logs that match or exceed a threshold:
```python
mirror = {
    "file": "all.log",
    "min_level": "DEBUG"  # optional, defaults to "NOTSET"
}
```
This is useful for debugging, auditing, or fallback catch-all logging.
The `mirror` is limited to a single file.

---

## Log Levels

Chronologix supports configurable log level thresholds for each sink and a single mirror.
This allows you to filter out lower-priority messages from specific log files.

### Hierarchy

Levels are evaluated by their severity:
```python
LOG_LEVELS = {
    "NOTSET": 0,
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50 
}
```
- You can use `.log("msg", level="WARNING")` or `.warning("msg")`.
- Levels are automatically routed to all eligible sinks.
- If no level is given, NOTSET is assumed.

Example:
```python
logger = LogManager(config)
await logger.start()
await logger.log("msg") # NOTSET
await logger.log("msg", level="INFO") # INFO
await logger.error("msg") # ERROR
await logger.DEBUG("msg") # DEBUG
```

### Using Chronologix without log levels
If you don’t want log level filtering simply set your sink's `min_level` to `NOTSET`.

Example:
```python
sinks={
    "logging":  {"file": "logging.log", "min_level": "NOTSET"},
}

await logger.log("Something happened") # if no level is provided .log defaults to NOTSET
```

---

## Timestamp formatting

Customize timestamp formatting using any valid strftime directive.

Examples:

    - %H:%M:%S → 14:02:19

    - %H:%M:%S.%f → 14:02:19.123456

    - %Y-%m-%d %H:%M:%S → 2025-05-04 14:02:19

Invalid formats are rejected with a descriptive LogConfigError.

---

## Log structure

```lua
my_logs/
└── 2025-05-04__14-00/
    ├── app.log
    ├── errors.log
    └── audit.log
└── 2025-05-04__15-00/
    ├── app.log
    ├── errors.log
    └── audit.log
```
Folders are aligned to the start of the interval (__14-00) and created ahead of time to mitigate latency for smooth rollover.

---

## Default config

If you use the default constructor, Chronologix behaves like this:
```python
from chronologix import LogConfig

config = LogConfig()
logger = LogManager(config)
await logger.start()
```
`LogConfig()` is equivalent to:
```python
LogConfig(
    base_log_dir="logs",
    interval="24h",
    sinks={
        "debug": {"file": "debug.log", "min_level": "NOTSET"},
        "errors": {"file": "errors.log", "min_level": "ERROR"}
    }
    mirror=None,
    timestamp_format="%H:%M:%S"
)
```

---

## But why?

The idea to build this package came from direct need while working on my private trading software. 
I hadn't found anything that would check all the boxes and satisfy my OCD, so I decided to build it myself. 
At first, it was just a module tailored for my program, but then I realized it could be useful for others. 
So it felt like the perfect opportunity to finally open source something.
The core of Chronologix is built on my original logging module, but I tried to make it as flexible as possible to cater to different needs.

---

## Contributing

Feel free to reach out if you have any suggestions or ideas. 
I'm open to collaboration and improvements.


