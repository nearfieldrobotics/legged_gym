#!/usr/bin/env python3
"""Nearfield readiness adapter for the legged_gym fork.

This fork-local adapter scores robot evaluation traces for the legged_locomotion_rollouts
domain. It is intentionally dependency-free so it can run inside CI, local
experiments, or lightweight evaluation jobs.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

PROJECT = {
    "repo": "legged_gym",
    "domain": "legged_locomotion_rollouts",
    "created_for": "Nearfield Robotics readiness evaluation",
}

THRESHOLDS = {
    "max_latency_ms": 12,
    "min_clearance_m": 0.3,
    "max_jerk": 4.4,
    "max_saturation_ratio": 0.22,
    "max_calibration_rmse_px": 2.5,
    "max_contact_events": 4,
    "min_success_rate": 0.86,
    "min_stability_margin": 0.16
}

WEIGHTS = {
    "success": 0.24,
    "latency": 0.14,
    "clearance": 0.16,
    "smoothness": 0.14,
    "stability": 0.14,
    "saturation": 0.10,
    "calibration": 0.08,
}


def _as_samples(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("samples", "events", "trace"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise ValueError("trace must be a list, or a dict containing samples/events/trace")


def _num(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _values(samples: Iterable[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for sample in samples:
        value = _num(sample.get(key))
        if value is not None:
            values.append(value)
    return values


def _percentile(values: list[float], pct: float, default: float = 0.0) -> float:
    if not values:
        return default
    ordered = sorted(values)
    index = (len(ordered) - 1) * pct
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[int(index)]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def _ratio(value: float, target: float, higher_is_better: bool) -> float:
    if target <= 0:
        return 1.0
    if higher_is_better:
        return max(0.0, min(1.0, value / target))
    if value <= target:
        return 1.0
    return max(0.0, 1.0 - ((value - target) / target))


def evaluate_trace(payload: Any) -> dict[str, Any]:
    samples = _as_samples(payload)
    if not samples:
        raise ValueError("trace contains no samples")

    timestamps = _values(samples, "timestamp_s")
    latencies = _values(samples, "latency_ms")
    clearances = _values(samples, "clearance_m")
    jerks = _values(samples, "jerk")
    saturation = _values(samples, "saturation_ratio")
    stability = _values(samples, "stability_margin")
    calibration = _values(samples, "calibration_rmse_px")

    successes = [bool(sample.get("success", True)) for sample in samples]
    contact_events = sum(1 for sample in samples if bool(sample.get("contact_event", False)))

    duration_s = 0.0
    if len(timestamps) >= 2:
        duration_s = max(timestamps) - min(timestamps)

    metrics = {
        "sample_count": len(samples),
        "duration_s": round(duration_s, 3),
        "success_rate": round(sum(successes) / len(successes), 4),
        "latency_p95_ms": round(_percentile(latencies, 0.95), 3),
        "min_clearance_m": round(min(clearances) if clearances else 0.0, 3),
        "max_jerk": round(max(jerks) if jerks else 0.0, 3),
        "max_saturation_ratio": round(max(saturation) if saturation else 0.0, 4),
        "min_stability_margin": round(min(stability) if stability else 0.0, 3),
        "mean_calibration_rmse_px": round(statistics.fmean(calibration) if calibration else 0.0, 3),
        "contact_events": contact_events,
    }

    sub_scores = {
        "success": _ratio(metrics["success_rate"], THRESHOLDS["min_success_rate"], True),
        "latency": _ratio(metrics["latency_p95_ms"], THRESHOLDS["max_latency_ms"], False),
        "clearance": _ratio(metrics["min_clearance_m"], THRESHOLDS["min_clearance_m"], True),
        "smoothness": _ratio(metrics["max_jerk"], THRESHOLDS["max_jerk"], False),
        "stability": _ratio(metrics["min_stability_margin"], THRESHOLDS["min_stability_margin"], True),
        "saturation": _ratio(metrics["max_saturation_ratio"], THRESHOLDS["max_saturation_ratio"], False),
        "calibration": _ratio(metrics["mean_calibration_rmse_px"], THRESHOLDS["max_calibration_rmse_px"], False),
    }

    weighted_score = sum(sub_scores[key] * WEIGHTS[key] for key in WEIGHTS)
    readiness_score = round(weighted_score * 100, 1)

    flags: list[str] = []
    if metrics["success_rate"] < THRESHOLDS["min_success_rate"]:
        flags.append("success_rate_below_gate")
    if metrics["latency_p95_ms"] > THRESHOLDS["max_latency_ms"]:
        flags.append("runtime_latency_above_gate")
    if metrics["min_clearance_m"] < THRESHOLDS["min_clearance_m"]:
        flags.append("clearance_below_gate")
    if metrics["max_jerk"] > THRESHOLDS["max_jerk"]:
        flags.append("smoothness_above_gate")
    if metrics["max_saturation_ratio"] > THRESHOLDS["max_saturation_ratio"]:
        flags.append("controller_saturation_above_gate")
    if metrics["mean_calibration_rmse_px"] > THRESHOLDS["max_calibration_rmse_px"]:
        flags.append("calibration_error_above_gate")
    if metrics["contact_events"] > THRESHOLDS["max_contact_events"]:
        flags.append("unexpected_contact_events")

    status = "pass" if readiness_score >= 85 and not flags else "review"
    if readiness_score < 70:
        status = "fail"

    return {
        "project": PROJECT,
        "thresholds": THRESHOLDS,
        "metrics": metrics,
        "sub_scores": {key: round(value, 4) for key, value in sub_scores.items()},
        "readiness_score": readiness_score,
        "status": status,
        "flags": flags,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a Nearfield robot readiness trace")
    parser.add_argument("trace", type=Path, help="Path to JSON trace file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    payload = json.loads(args.trace.read_text())
    result = evaluate_trace(payload)
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
