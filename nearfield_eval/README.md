# Nearfield evaluation adapter

This fork-local adapter adds a small, runnable readiness scoring utility for the legged_gym fork.

It is not a claim of upstream ownership and it is not intended to change the original project's core behavior. It gives Nearfield a concrete integration surface for testing how legged_gym could contribute evidence to a robot readiness report.

## What it does

- Reads a JSON robot trace from a scenario run.
- Computes success, latency, clearance, smoothness, stability, saturation, calibration, and contact-event metrics.
- Produces a readiness score plus review flags.
- Keeps thresholds project-specific for the legged_locomotion_rollouts domain.

## Run

```bash
python3 nearfield_eval/readiness_adapter.py nearfield_eval/sample_trace.json --pretty
```

## Why this matters

Nearfield evaluates whether a robot is ready for real deployment by looking for replayable evidence, not one-off demos. This adapter is a first integration stub for turning traces from this project into structured evaluation output.
