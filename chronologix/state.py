# state.py

from pathlib import Path
from typing import Dict, List, Optional
from chronologix.config import LOG_LEVELS


class LogState:
    """
    Holds the resolved file path mapping for sinks and mirror.
    Used as the single source of truth across rollover and write operations.
    """

    def __init__(self):
        # individual sink paths, set fresh on each rollover
        self._sink_paths: Dict[str, Path] = {}

        # optional mirror path
        self._mirror_path: Optional[Path] = None

        # precomputed level → list of paths
        self._paths_by_level: Dict[str, List[Path]] = {}

    def update_active_paths(
        self,
        sink_paths: Dict[str, Path],
        mirror_path: Optional[Path],
        sink_levels: Dict[str, int],
        mirror_threshold: Optional[int]
    ) -> None:
        """
        Set active paths for all sinks and optional mirror,
        and precompute level-based path dispatch map.
        """
        self._sink_paths = sink_paths
        self._mirror_path = mirror_path
        self._paths_by_level.clear()

        # for each log level, build the list of files that should receive logs of that level
        for level_name, level_value in LOG_LEVELS.items():
            paths: List[Path] = []

            for sink_name, min_level in sink_levels.items():
                if level_value >= min_level: # sink is eligible for this level, add its path
                    path = sink_paths.get(sink_name)
                    if path:
                        paths.append(path)

            if mirror_path and mirror_threshold is not None:
                if level_value >= mirror_threshold:
                    paths.append(mirror_path)

            self._paths_by_level[level_name] = paths

    def get_paths_for_level(self, level: str) -> List[Path]:
        """Return list of resolved paths for given level (sinks + mirror)."""
        if level not in self._paths_by_level:
            raise ValueError(f"Unknown log level: '{level}'")

        return self._paths_by_level[level].copy()
