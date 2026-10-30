# External interface contracts

JSON only. Unknown fields, type coercion, negative ranges, invalid categories and inconsistent exemption claims fail before enqueueing. `Bid.model_json_schema()` is exported in contracts/bid.schema.json; FastAPI exposes the full OpenAPI schema at /openapi.json. Authenticated API requests use `Authorization: Bearer <API_TOKEN>` when configured. The current service has one shared demo token, not multi-tenant ownership isolation.

## POST /v1/runs
Input: examples/valid.json and the Bid schema. Five integer INR turnovers correspond exactly to FY2019-20, 2020-21, 2021-22, 2022-23, 2023-24. eligible_orders counts implemented desktop orders in that period for the specified eligible public institutions. These are declarations; the system does not authenticate certificates or inspect uploaded bid documents. recognition_id is an identifier supplied by the caller, not a registry verification result. EMD exemption requires category mse/startup and a nonempty recognition_id at ingestion. No credentials should be entered in notes.

202: run_id, status queued, correlation_id, poll_path. Poll GET /v1/runs/{id}. A queued response does not mean screening success. 422: quarantine_id, field errors and agent_started=false. 401: invalid token. 429: rate limit with Retry-After. 413: body above 64 KiB after reading the body; reverse proxy must enforce a streaming size limit for hostile traffic. 503/dependency errors need a retry after inspecting health; there is no implicit successful run.

## GET /v1/runs/{id}
404 for an unknown ID. status is queued, researching, verifying or completed. Completed can contain an escalation due to failure; inspect result.verification.passed and result.basis. Returns the stored bid summary, recommendation, condition findings, citations, prompt version, timings and available cost. Result routes: pass-to-technical-evaluation; seek-clarification; reject-with-cited-condition. The last is a recommendation for committee consideration, never an actual rejection. human_review=true always. Citation fields include id, file, local PDF page, original PDF page, section, source URL and exact normalised text.

## GET /v1/runs/{id}/trace
Returns ordered events with correlation ID, process ID, agent, tool, query, retrieved passages, prompt version, latency, retry attempts, token usage and cost when available. These persisted events are the detailed audit trail; OpenTelemetry supplies worker-stage spans with run ID attributes. Cross-service parent-child span propagation is not implemented.

## POST /v1/runs/{id}/feedback
Input {satisfactory: boolean, reason: string length 3..1000}. Requires completed run; otherwise 409. Persists one latest feedback per run; a repeated post replaces that run's feedback. Returns 201 {saved:true}. Reasons are stored, never fed to the model.

## GET /v1/dashboard
Persisted run counts, quarantine count, feedback totals, worker heartbeats and recent automatic citation resolution scores. Full deterministic reference scoring is in the evaluation CLI; the live score is only a proxy.

## GET /health and GET /metrics
Health checks store read/write reachability; it is not an assertion that a model is available. Prometheus text metrics include complete-run histogram and corpus freshness. Worker metrics include task counts, success/failure labels, task latency, tools, steps, retries and uptime. Container CPU/memory and Redis metrics come from the default internal resource exporter.

## Provider and queue
Provider: configurable HTTP chat-completions JSON messages, JSON tool-action content and optional usage.prompt_tokens/completion_tokens. Only four action names are accepted: corpus_search, clause_lookup, request_fields, handoff. No shell or network tools are exposed to the model. A shared Redis sorted-set queue or local SQLite jobs table carries run IDs. Each claimed job has a 60-second lease; acknowledgment occurs after persisted handoff/result. Worker handoff state contains validated bid, retrieved clause map, phase, loop limits and timestamps. At-least-once delivery is possible; workers skip completed runs. Exactly-once handoff under all crash races is not claimed.
