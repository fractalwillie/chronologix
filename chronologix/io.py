# io.py

import asyncio
import io
import os
from pathlib import Path
from typing import Dict, Iterable, Tuple
from chronologix.errors import internal_log


def prepare_directory(base_dir: Path, folder_name: str, sink_names: Iterable[str]) -> Dict[str, Path]:
    """
    Create log folder and check if .log files for all sinks exist.
    Return sink_name → full Path map.
    """
    # check if the log subdirs exists
    target_folder = base_dir / folder_name
    target_folder.mkdir(parents=True, exist_ok=True)

    path_map: Dict[str, Path] = {}

    for name in sink_names:
        # touch each log file to make sure it exists
        log_file = target_folder / name
        if not log_file.exists():
            log_file.touch(exist_ok=True)
        path_map[name] = log_file

    return path_map


class BufferedWriter:
    """
    Asynchronous buffered writer for file-based logging.
    Queues log messages and writes them in batches with periodic flushing.
    """

    def __init__(self, flush_interval: float = 0.1, max_batch: int = 1024):
        """Initialize the async buffered writer."""
        self._queue: asyncio.Queue[Tuple[Path, str]] = asyncio.Queue(maxsize=max_batch)
        self._task: asyncio.Task | None = None
        self._flush_interval = flush_interval
        self._handles: Dict[Path, 'io.TextIOWrapper'] = {}
        self._running = False


    def start(self) -> None:
        """Start the background writer task that consumes the message queue."""
        if not self._task:
            self._running = True
            self._task = asyncio.create_task(self._run())


    async def write(self, path: Path, txt: str) -> None:
        """Enqueue a message for writing to the given file path."""
        await self._queue.put((path, txt))


    async def stop(self) -> None:
        """Stop the writer task gracefully, flush all messages, and close all file handles."""
        self._running = False
        if self._task:
            await self._queue.join()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

            for path, f in self._handles.items():
                try:
                    f.flush()
                    os.fsync(f.fileno())
                    f.close()
                except Exception as e:
                    internal_log(f"Close error for {path}: {e}")



    async def _run(self) -> None:
        """
        Background loop that dequeues messages and writes them to file.
        Flushes buffers periodically to reduce latency.
        """
        try:
            while True:
                try:
                    path, txt = await asyncio.wait_for(self._queue.get(), timeout=self._flush_interval)
                except asyncio.TimeoutError:
                    self._flush_all()
                    continue

                fh = self._handles.get(path)
                if fh is None:
                    try:
                        fh = open(path, "a", encoding="utf-8")
                        self._handles[path] = fh
                    except Exception as e:
                        internal_log(f"Failed to open log file {path}: {e}")
                        self._queue.task_done()
                        continue

                try:
                    fh.write(txt)
                except Exception as e:
                    internal_log(f"Write error for {path}: {e}")
                finally:
                    self._queue.task_done()
        finally:
            self._flush_all()


    def _flush_all(self):
        """Flush all open file handles to disk."""
        for path, f in self._handles.items():
            try:
                f.flush()
            except Exception as e:
                internal_log(f"Flush error for {path}: {e}")


    async def flush(self) -> None:
        """
        Wait for all queued messages to be written, flush buffers to disk,
        and close all file handles. Used during rollovers to prevent cross-chunk writes.
        """
        await self._queue.join()

        for path, f in list(self._handles.items()):
            try:
                f.flush()
                os.fsync(f.fileno())
                f.close()
            except Exception as e:
                internal_log(f"Flush+Close error for {path}: {e}")
            finally:
                del self._handles[path]

