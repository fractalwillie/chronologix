# state.py

from pathlib import Path
from typing import Dict, List


class LogState:
    """
    Holds the active log path mapping for each stream, including mirroring.
    Used as the single source of truth across rollover and write operations.
    """

    def __init__(self, log_streams: List[str], mirror_map: Dict[str, List[str]]):
        """Initialize stream and mirror mapping. Holds current active log paths."""
        self._log_streams = set(log_streams)
        self._mirror_map = mirror_map
        self._stream_to_paths: Dict[str, List[Path]] = {}

    def update_active_paths(self, path_map: Dict[str, Path]) -> None:
        """Set active paths for each stream and mirror target using new path map."""
        self._stream_to_paths.clear() # reset active mapping before applying updated paths

        for stream in self._log_streams:
            paths: List[Path] = []

            # always include stream's own log path
            if stream in path_map:
                paths.append(path_map[stream])

            # if stream is source of mirroring, add all mirror targets
            if stream in self._mirror_map:
                for mirror_target in self._mirror_map[stream]:
                    if mirror_target not in path_map:
                        raise ValueError(
                            f"Mirror target '{mirror_target}' not in active path map"
                        )
                    paths.append(path_map[mirror_target])

            if paths:
                self._stream_to_paths[stream] = paths

    def get_all_resolved_paths(self) -> Dict[str, List[Path]]:
        """Return copy of current stream → file path lists."""
        return self._stream_to_paths.copy()
