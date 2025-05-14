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
-  Optional terminal output (stdout/stderr) with level filtering
-  Optional time-based log deletion (retain policy)
-  Optional output format control (`text` or `json`) per sink/mirror
-  Optional automatic log compression (`zip` or `tar.gz`) on every rollover
-  Custom core, no dependance on Python's logging module, no global state

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
        "app": {"file": "app.json", "min_level": "INFO", "format": "json"}, # logs INFO and above into app.json file
        "errors": {"file": "errors.json", "min_level": "ERROR", "format": "json"}, # logs ERROR and above into errors.json file
    },
    mirror={
        "file": "audit.json",  # captures all messages regardless of sink
        "min_level": "NOTSET", # optional: "min_level": "NOTSET" defaults to "NOTSET" if not specified
        "format": "json" # optional: "format": "json" defaults to "text" if not specified
    },
    cli_echo={
        "enabled": True,  # print all logs to terminal (stdout)
        # optional: "min_level": "INFO" defaults to NOTSET if not specified
    },
    timestamp_format="%H:%M:%S.%f",
    retain="1h", # deletes log folders older than 1 hour
    compression={
        "enabled": True,
        "compress_format": "tar.gz"  # optional, defaults to "zip" if omitted
    }
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
- Two new folder per hour like "2025-05-04__14-00/" and "2025-05-04__15-00/" inside my_logs/
- Three log files inside each: app.json (INFO and above), errors.json (ERROR and above), audit.json (NOTSET)
- All logs formatted as json objects - {"timestamp": "14:02:19:287248", "level": "INFO", "message": "Some msg"}
- The exception will be logged to both sinks and mirror.
- Messages without level (like "Some NOTSET level msg") will be treated as NOTSET and only land in sinks that accept that level (here: audit.json mirror file).
- Level filtering and routing is automatic. You don’t specify a target sink, only a level (or nothing).
- All logs reflected in terminal through stdout.
- All subfolders inside my_logs/ are parsed on every rollover. Those older than 1 hour are deleted.
- The subfolder from the previous interval will be compressed into .tar.gz before cleanup on every rollover
- Compressed archives are saved next to their original folder (e.g., 2025-05-04__14-00.zip)

---

## Path structure

You can set the log output folder using either a string path or a `pathlib.Path` object.

Examples:
```python
LogConfig(base_log_dir="logs")  # relative to current working dir
LogConfig(base_log_dir="/var/log/chronologix")  # absolute path (Linux)
LogConfig(base_log_dir=Path("~/.chronologix").expanduser())  # user home dir
```
Chronologix will create any missing folders automatically.

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
- a `file` name (relative to the chunk folder) and file extension (`.log`, `.txt`, `.json`, `.jsonl`)
- a `min_level` that controls what gets written (`NOTSET`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- a `format` (`text` or `json`) that controls the output structure. It's optional and defaults to `text` when not included

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
    "format": "text" # optional, defaults to "text" if not included, can be set to "json" for JSON output format
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

## Log format & file extensions

You can control the output format of each log file individually.

Supported `format`:
- `"text"` (default)
- `"json"`

Supported `file` extensions:
- `.txt`
- `.log`
- `.json`
- `.jsonl`

To enable JSON output:
```python
sinks={
    "debug": {"file": "debug.json", "min_level": "DEBUG", "format": "json"},
},
mirror={
    "file": "all.json",
    "format": "json"
}
```
Each log message will then be written as a JSON object:
```json
{"timestamp": "14:02:19.123456", "level": "INFO", "message": "Some INFO level msg"}
```

- `format` is optional and defaults to `"text"` if not specified

- `file` extension doesn't need to match `format` (e.g., you can have `debug.txt` in JSON `format`)

- `cli_echo` always uses `text` format regardless of `format` settings

---

## Terminal output

Chronologix can optionally echo log messages to your terminal.

This can be useful during development or debugging when you want to see logs in real-time, while still keeping structured log files.

You can configure this with the `cli_echo` option:

### Simple format
Print to stdout only:
```python
cli_echo = {
    "enabled": True,
    "min_level": "INFO"  # optional, defaults to NOTSET
}
```

### Advanced format
Split logs between stdout and stderr:
```python
cli_echo = {
    "stdout": {"min_level": "INFO"},     # INFO and WARNING go to stdout
    "stderr": {"min_level": "ERROR"}     # ERROR and CRITICAL go to stderr
}
```

- You can use stdout/stderr individually, or both.
- `stderr` takes precedence if a message qualifies for both.
- If `enabled: False` or no config is provided, terminal output is disabled.

---

## Time-based log deletion

Automate log cleanup by setting `retain` parameter in LogConfig.

Example:
```python
LogConfig(
    retain="1h"
)
```
The subfolders in which the logs are nested are parsed on every rollover, and those older than 1 hour are deleted.

Supported time units:
- `m` - minutes
- `h` - hours
- `d` - days
- `w` - weeks

`retain` is disabled in default config.

If both compression and retention are configured, compression **always runs before** cleanup to avoid deleting subfolders mid-archive.

**Important**: `retain` must be equal to or longer than the rollover `interval`.

---

## Log compression

Automate compression of previous log subfolders after each rollover.
Reduce disk usage without needing to implement your own compression logic.

### Enabling compression

To enable log compression, provide a `compression` config:
```python
compression={
    "enabled": True  # enables compression using default format: zip
}
```
Or specify a format:
```python
compression={
    "enabled": True,
    "compress_format": "tar.gz"  # or "zip"
}
```

If you want to delete the original log subfolder after compression, configure `retain` with the same amount of time as the rollover `interval` (e.g. `interval="24h"` and `retain="1d"`).

### Behavior

- On every rollover, the subfolder from the previous time interval is compressed
- Compression runs before log deletion (if `retain` is enabled)
- Compressed archives are saved next to log folders (e.g. `2025-05-04__14-00.zip`)
- Already-compressed folders are skipped on future rollovers
- The current and next interval folders are never compressed
- Compression supports both `.zip` and `.tar.gz` using Python’s built-in libraries

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
    },
    mirror=None,
    timestamp_format="%H:%M:%S",
    cli_echo=None,
    retain=None,
    compression=None
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


