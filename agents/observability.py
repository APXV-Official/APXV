"""
APXV — Optional Observability Helpers (BYO / DIY)

This module provides simple helper functions for users who want to
build their own metrics or export logs to external systems.

It is completely optional and not used by the core APX runtime.

All code is original work written for APXV.
"""

import json
from pathlib import Path
from typing import Dict, Any, List


def get_log_metrics(log_path: Path) -> Dict[str, Any]:
    """
    Parse a structured JSON audit log and return basic metrics.

    Returns counts by event_type, plus aggregate cost/latency if present.
    """
    if not log_path.exists():
        return {"error": "Log file not found"}

    event_counts: Dict[str, int] = {}
    total_cost = 0.0
    total_latency = 0
    count_with_cost = 0
    count_with_latency = 0

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            event_type = entry.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

            data = entry.get("data", {})
            if "cost_usd" in data:
                total_cost += data["cost_usd"]
                count_with_cost += 1
            if "latency_ms" in data:
                total_latency += data["latency_ms"]
                count_with_latency += 1

    return {
        "event_counts": event_counts,
        "total_cost_usd": round(total_cost, 6),
        "avg_cost_usd": round(total_cost / count_with_cost, 6) if count_with_cost > 0 else 0,
        "total_latency_ms": total_latency,
        "avg_latency_ms": round(total_latency / count_with_latency) if count_with_latency > 0 else 0,
    }


def export_to_prometheus(metrics: Dict[str, Any], prefix: str = "apx") -> str:
    """
    Convert basic metrics into a simple Prometheus text format.

    Returns a string that can be exposed via an HTTP endpoint or written to a file.
    """
    lines = []

    for event, count in metrics.get("event_counts", {}).items():
        lines.append(f'{prefix}_event_total{{event="{event}"}} {count}')

    if metrics.get("total_cost_usd"):
        lines.append(f"{prefix}_total_cost_usd {metrics['total_cost_usd']}")
    if metrics.get("avg_cost_usd"):
        lines.append(f"{prefix}_avg_cost_usd {metrics['avg_cost_usd']}")
    if metrics.get("total_latency_ms"):
        lines.append(f"{prefix}_total_latency_ms {metrics['total_latency_ms']}")
    if metrics.get("avg_latency_ms"):
        lines.append(f"{prefix}_avg_latency_ms {metrics['avg_latency_ms']}")

    return "\n".join(lines)