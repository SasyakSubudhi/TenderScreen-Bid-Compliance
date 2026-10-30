# Operational runbook

## Provider errors or circuit open

The API can remain healthy because its health endpoint checks storage, not successful model inference. Inspect a failed run trace for model_error, provider_failed, circuit_open, loop bounds or deadline. Confirm runtime profile and FAULT_PROVIDER before restarting. Three provider attempts use bounded timeout and 0.1/0.2 second backoff. Two exhausted calls open the shared breaker for 15 seconds. Fix the dependency, preserve Redis and volumes, allow cooldown, submit a new reference case and require verification.passed=true before claiming recovery. Never relabel the earlier failed run.

For controlled stub fault injection change FAULT_PROVIDER in the private .env, recreate only provider-stub, exercise failures, restore FAULT_PROVIDER=0, recreate provider-stub, wait for cooldown and verify a fresh successful run. Do this only in the fictional isolated demo deployment. The recorded outage/recovery artifact contains actual results.

## Stalled worker or growing queue

Inspect /v1/dashboard heartbeats and Grafana per-agent task/step latency. Containers have distinct hostnames even when both show PID 1. Check research and verification independently. A Redis lease expires after 60 seconds; the run deadline is 45 seconds including queueing. Persisted completed stages are skipped on redelivery. Preserve AOF and named volumes, restart a failed worker and verify a new result. At-least-once delivery permits duplicate events and does not guarantee exactly-once handoff.

## WSL or build trouble

Keep foreground Compose or Ubuntu active during a demonstration: WSL idle shutdown previously stopped containers. RUN_DEMO.cmd keeps foreground Compose open. On the measured host bridge DNS stalled package downloads; the configuration generator supports --build-network host. Do not disable TLS verification or erase evidence volumes to make a failed build disappear. One-shot indexer/model-init services normally exit with code 0. A local model needs adequate RAM and CPU/GPU capacity; the measured CPU batch missed deadlines and must be described honestly.

## Restore a normal demonstration

Set FAULT_PROVIDER=0, restore intended rate limits and cache setting, run the correct Compose profile, wait for health, submit ordinary and startup examples, inspect verification and exact citations, and open Grafana/Jaeger. All official procurement decisions remain human.
