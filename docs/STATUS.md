# Requirement and evidence map

| Area | Implemented and exercised | Evidence and limits |
|---|---|---|
| Interface | FastAPI asynchronous 202 + polling, strict bid/feedback schemas, quarantine before agents, auth/rate limits | contracts/, tests/, docker_stub_smoke.json; caller declarations are not certificate authentication |
| Agents | Separate research and verifier containers, LangGraph, three evidence tools, bounded loop, handoff, one repair, safe escalation | live and stub smoke traces; final_browser_check.json; finite deterministic verifier |
| Corpus | Four official source PDFs, hashes and page mappings, LangChain/FAISS, hash and real semantic embeddings, incremental updates | corpus/manifest.json, incremental_semantic.json; live tools query ten curated clauses rather than all full-index chunks |
| Quality | 24 fixed cases per variant, four explicit metrics, v1/v2 deliberate policy change, sampled live scores, feedback | evaluation.json, live_evaluation.json; proxies are not independent legal judgement |
| Runtime | Eleven base Compose services, live model overlay, separate replicable workers, runtime secret configuration | clean_clone.json and logs; dependency images/layers were cached, not a clean-machine claim |
| Observability | Connected API/research/verifier OTel traces, Prometheus, 17-panel Grafana dashboard, CPU/memory and Redis exporter | observability.json, final_observability.json, resource_sample.json |
| Performance | Predeclared 30 s E2E p95 target, actual Locust one/three-worker matrix, saturation and cache cases | load_plan.json, load_matrix.json, benchmark CSV/log files; short single-host repetitions include draining |
| Reliability | Timeouts, three attempts, backoff, shared breaker, leased queue, actual outage/recovery | outage_recovery.json, RUNBOOK.md, INCIDENTS.md; at-least-once delivery and limited cancellation |
| Actual inference | Ollama local chat model and 768-dimensional nomic embeddings, actual reported tokens and local fee scope | live_costs.json, deployment_profile.json; real CPU batch degraded under timeouts and breaker carryover |
| Publication and study material | Public source, passing source CI, anonymous clone rehearsal, final report and comprehensive guide | public repository, clean_clone.json; 34-page guide with 70 viva answers and 3-page report |

Human committee review always owns final decisions. Current legal consolidation, certificate authenticity, broader reviewed rules, stronger semantic guardrails and production identity controls remain outside this teaching service.
