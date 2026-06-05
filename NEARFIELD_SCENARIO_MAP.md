# Nearfield scenario map: legged_gym

Date: 2026-06-05

This fork-local note records how legged_gym can inform Nearfield's robot readiness evaluation work. It is a project-specific research note, not an upstream authorship claim and not a request to merge changes upstream.

## Relevance

legged_gym is relevant to readiness evaluation because it touches legged locomotion training environments, rollout evaluation, and sim-to-real locomotion preparation. Nearfield uses this kind of open-source stack review to identify where deployment evidence can be captured before a robot is trusted in shared human spaces.

## Evaluation hooks

- gait stability metrics
- terrain randomization records
- fall/recovery taxonomy

## Scenario candidates

- legged robot readiness over uneven floors
- payload and disturbance trials in simulation
- locomotion policy regression tracking

## Nearfield use

For Nearfield, the important question is not whether a robot succeeds once. The useful signal is whether a scenario can be replayed, scored, compared, and turned into evidence that operators can inspect. This repository helps map one part of that evidence pipeline.
