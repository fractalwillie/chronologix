# Chronologix

Chronologix is a fully asynchronous, modular logging system for Python.

It writes structured log files across multiple named streams, supports time-based chunking, and avoids the standard logging module completely.

---

## Features

-  Fully async logging 
-  Time-based rollover (e.g. every 24h, 1h, 15min)
-  Log stream isolation (e.g. `errors`, `debug`, `events`)
-  Configurable mirror streams (`errors` → `debug`)
-  Safe, stateless async file writes
-  Config validation with clear error feedback
-  Custom log paths via `str` or `pathlib.Path`
-  Predictable file and folder structure for automated processing

---

## Installation

Chronologix requires **Python 3.7+**.

```bash
pip install chronologix
```

---

## Usage example

```python
from chronologix import LogConfig, LogManager

config = LogConfig(
    base_log_dir="my_logs",                 # can also be a pathlib.Path
    interval="1h",                          # rollover interval
    log_streams=["app", "errors", "audit"], # named log streams
    mirror_map={"errors": ["app"]},         # errors are mirrored into "app"
    timestamp_format="%H:%M:%S.%f"          # timestamp format
)

logger = LogManager(config)

async def divide(a, b):
    try:
        result = a / b
        await logger.log(f"Division result: {result}", target="app")
    except Exception as e:
        await logger.log(f"Exception occurred: {e}", target="errors")

async def main():
    await logger.start()
    await logger.log("Starting batch job", target="app")
    await logger.log("Auditing step 1", target="audit")
    await divide(10, 0)  # this will raise and log to both "errors" and "app"
    await logger.stop()

```
This example will produce following:
- A new folder per hour like: 2025-05-04__14-00/
- Three log files inside: app.log, errors.log, audit.log
- The exception will be logged to both errors.log and app.log
- The audit message will only go to audit.log with no mirroring

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

Each interval corresponds to a different granularity of time-based chunking.
- `interval="24h"` → folders like `2025-05-04/`
- `interval="1h"` → folders like `2025-05-04__14-00/`

---

## Log streams

Log streams define the named `.log` files Chronologix will manage.

Each stream corresponds to a separate log file inside each time-based folder.

Example:
```python
log_streams=["app", "errors", "audit"]
```
This would create:
```lua
my_logs/
└── 2025-05-04/
    ├── app.log
    ├── errors.log
    └── audit.log
```
Each call to .log(message, target=...) writes to the stream you specify.

You can define as many log streams as needed or just a single one.

Example:
```python
LogConfig(
    log_streams=["app"],
    mirror_map={}
)
```
This will create a single `app.log` file per interval.
Mirroring is optional, and is not required when using only one stream.

---

## Mirroring

Mirroring can be configured like this:
```python
mirror_map = {
    "errors": ["app"],    # messages logged to "errors" will mirror to "app"
    "debug":  ["all"]
}
```
Mirroring is optional. Any stream can exist without mirrors, and mirrors can point to multiple targets.

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
Which is equivalent to:
```python
LogConfig(
    base_log_dir="logs",
    interval="24h",
    log_streams=["all", "errors"],
    mirror_map={"errors": ["all"]},
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


