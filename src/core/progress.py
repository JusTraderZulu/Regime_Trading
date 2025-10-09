"""
Progress tracking and timing utilities for pipeline execution.
Provides real-time feedback and performance metrics.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class NodeTiming:
    """Timing data for a single pipeline node"""
    node_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: str = "running"  # running, completed, failed
    
    def complete(self):
        """Mark node as completed and calculate duration"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = "completed"
    
    def fail(self):
        """Mark node as failed"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = "failed"


@dataclass
class PipelineProgress:
    """Track progress and timing for entire pipeline"""
    symbol: str
    mode: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    node_timings: Dict[str, NodeTiming] = field(default_factory=dict)
    total_nodes: int = 10
    
    @property
    def elapsed_time(self) -> float:
        """Get total elapsed time so far"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def completed_nodes(self) -> int:
        """Count completed nodes"""
        return sum(1 for t in self.node_timings.values() if t.status == "completed")
    
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage"""
        return (self.completed_nodes / self.total_nodes) * 100
    
    def start_node(self, node_name: str):
        """Start timing a node"""
        self.node_timings[node_name] = NodeTiming(
            node_name=node_name,
            start_time=time.time()
        )
        
        # Log progress
        logger.info(
            f"[{self.completed_nodes + 1}/{self.total_nodes}] "
            f"{node_name}... ({self.progress_percent:.0f}% complete)"
        )
    
    def complete_node(self, node_name: str):
        """Mark node as completed"""
        if node_name in self.node_timings:
            self.node_timings[node_name].complete()
            timing = self.node_timings[node_name]
            logger.info(
                f"✓ {node_name} completed in {timing.duration:.1f}s"
            )
    
    def fail_node(self, node_name: str, error: str):
        """Mark node as failed"""
        if node_name in self.node_timings:
            self.node_timings[node_name].fail()
            timing = self.node_timings[node_name]
            logger.error(
                f"✗ {node_name} failed after {timing.duration:.1f}s: {error}"
            )
    
    def complete_pipeline(self):
        """Mark entire pipeline as complete"""
        self.end_time = time.time()
        
        # Log summary
        logger.info("=" * 60)
        logger.info("Pipeline Execution Summary:")
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Mode: {self.mode}")
        logger.info(f"Total Time: {self.elapsed_time:.1f}s")
        logger.info(f"Completed: {self.completed_nodes}/{self.total_nodes} nodes")
        logger.info("=" * 60)
        
        # Log detailed breakdown
        logger.info("Timing Breakdown:")
        for node_name, timing in self.node_timings.items():
            status_icon = "✓" if timing.status == "completed" else "✗"
            logger.info(
                f"  {status_icon} {node_name}: {timing.duration:.1f}s "
                f"({(timing.duration / self.elapsed_time * 100):.1f}%)"
            )
        logger.info("=" * 60)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for state storage"""
        return {
            "symbol": self.symbol,
            "mode": self.mode,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_time": self.elapsed_time,
            "total_nodes": self.total_nodes,
            "completed_nodes": self.completed_nodes,
            "progress_percent": self.progress_percent,
            "node_timings": {
                name: {
                    "duration": t.duration,
                    "status": t.status,
                }
                for name, t in self.node_timings.items()
            }
        }


@contextmanager
def track_node(progress: PipelineProgress, node_name: str):
    """
    Context manager for tracking node execution.
    
    Usage:
        with track_node(progress, "load_data"):
            # ... node code ...
    """
    progress.start_node(node_name)
    try:
        yield
        progress.complete_node(node_name)
    except Exception as e:
        progress.fail_node(node_name, str(e))
        raise


def format_progress_bar(percent: float, width: int = 40) -> str:
    """
    Create ASCII progress bar.
    
    Args:
        percent: Progress percentage (0-100)
        width: Width of bar in characters
    
    Returns:
        Formatted progress bar string
    
    Example:
        >>> format_progress_bar(75, 40)
        '[████████████████████████████████        ] 75%'
    """
    filled = int(width * percent / 100)
    empty = width - filled
    bar = "█" * filled + " " * empty
    return f"[{bar}] {percent:.0f}%"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted string (e.g., "1m 34s", "45s", "2h 15m")
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def estimate_remaining_time(progress: PipelineProgress) -> Optional[float]:
    """
    Estimate remaining time based on average node duration.
    
    Args:
        progress: Pipeline progress tracker
    
    Returns:
        Estimated seconds remaining, or None if not enough data
    """
    completed = progress.completed_nodes
    if completed == 0:
        return None
    
    # Calculate average time per node
    avg_time = progress.elapsed_time / completed
    
    # Estimate remaining
    remaining_nodes = progress.total_nodes - completed
    estimated = avg_time * remaining_nodes
    
    return estimated


def print_progress_update(progress: PipelineProgress):
    """
    Print a formatted progress update.
    
    Args:
        progress: Pipeline progress tracker
    """
    bar = format_progress_bar(progress.progress_percent)
    elapsed = format_duration(progress.elapsed_time)
    
    remaining_est = estimate_remaining_time(progress)
    remaining_str = ""
    if remaining_est:
        remaining_str = f" | ETA: {format_duration(remaining_est)}"
    
    print(
        f"\r{bar} | Elapsed: {elapsed}{remaining_str}",
        end="",
        flush=True
    )

