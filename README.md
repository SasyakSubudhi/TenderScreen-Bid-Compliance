# TenderScreen

Public procurement bid compliance screening service for UE24AM342AA5 Mini Project 06.

Team: **PES1UG24AM256 · PES1UG24AM266 · PES1UG24AM269 · PES1UG24AM292**.

The service screens bids for closed IIT Palakkad tender TENDER/2024-25/370. It returns per-condition findings with exact source quotations and page references. A startup or MSE policy conflict is escalated with both sources. The human tender committee owns every final decision.

## Quick Windows demonstration

Double-click `RUN_DEMO.cmd` for the repeatable delayed-stub profile. It supports Docker Desktop or the tested WSL Ubuntu installation and keeps Compose in the foreground. Read API_PORT and API_TOKEN in the generated private `.env`, open the local web address and submit a fictional example.

## Run the live model deployment

Install Docker with Linux containers, Compose v2 and Python 3.12. Open a terminal in this folder:

```sh
python scripts/configure.py --mode local --model llama3.2:latest --embedding-model nomic-embed-text:latest --output .env.live
docker compose --env-file .env.live -f compose.yaml -f compose.live.yaml up --build
```

The model identifiers above describe the tested experiment; runtime settings and credentials are supplied through the generated private environment file. The initializer downloads the requested models into a persistent volume. First startup requires internet access and several GB of disk and RAM. Tests used CPU inference, not a GPU. The full live CPU batch suffered timeouts and breaker carryover; use the recorded failures when discussing quality and do not claim this profile met the latency SLO. On the tested WSL host, use `--build-network host` when generating configuration if bridge DNS fails, and keep Ubuntu or foreground Compose running to prevent WSL idle shutdown.

Open `http://localhost:8000`. Copy API_TOKEN from `.env.live` into the token field. Select Ordinary bidder or Startup conflict and start screening. The web client shows the run state, cited findings, verification, trace and feedback. `/docs` provides the REST contract. Change the host port with the configuration generator's `--port` option.

Grafana runs on port 3000 with user `admin` and GRAFANA_ADMIN_PASSWORD from the private file. Prometheus is on 9090 and Jaeger on 16686. The resource exporter is internal; it reads container statistics through a read-only Docker socket mount. It should remain inside this trusted local deployment.

Stop using the same Compose options followed by `down`. Named volumes preserve data; omit `-v` unless deletion is intended. Configuration files are deliberately excluded from Git and the ZIP.

## Reproducible delayed stub

```sh
python scripts/configure.py
docker compose up --build
```

This profile uses a 0.5-second HTTP model stub and 512-dimensional signed hash embeddings. It is a controlled benchmark dependency. The live profile uses actual local chat inference and 768-dimensional semantic embeddings. Neither profile trains a model.

## Architecture and behavior

FastAPI validates and quarantines input before adding jobs to Redis. A separate LangGraph research worker chooses bounded tools: inspect bid fields, retrieve clauses and follow exact clause IDs. It hands off persisted state to a separate verifier container. The verifier checks the finite tender contract and exact citations, performs one bounded evidence repair and escalates unresolved cases. Redis leases allow recovery after a worker disappears; delivery is at least once.

The official PDFs have source URLs, hashes and page mappings. Corpus ingestion uses 1100-character windows with 150-character overlap. FAISS holds the vector index. Repeated ingestion reuses unchanged embeddings; `python -m app.corpus --reembed-chunk CHUNK_ID` refreshes a selected chunk. Live screening searches a small curated clause index whose quotations are checked against the original PDFs. The full PDF index supports corpus operations. This is a finite contract, not unrestricted legal document interpretation.

Runtime limits are 12 research steps, 10 tools and a 45-second run deadline including queue wait. Provider calls have timeouts, three attempts, exponential backoff and a shared circuit breaker. OpenTelemetry propagates trace context across services. Prometheus/Grafana report per-agent latency, token usage, costs, container CPU/memory and Redis health.

## Verification and measurements

23 automated tests cover contracts, quarantine, authentication/rate protection, citation tampering, evidence repair, incomplete-run escalation and targeted index updates. `evidence/docker_live_smoke.json` records actual HTTP runs with real local inference and distinct agent container identities. `evidence/observability.json` records healthy scrape targets, the provisioned dashboard and traces spanning three services.

```sh
python -m pytest tests -q
python -m scripts.evaluate
python -m app.corpus
```

The evaluator compares prompt v1 with v2 on 24 fixed cases each. Groundedness, context precision, faithfulness and hallucination are explicit finite-reference proxies; they do not establish general legal correctness. Token usage comes from actual provider responses, and local provider fees exclude electricity and hardware.

The predeclared performance target is complete-run p95 <= 30 seconds. The 45-second hard deadline is a separate safety limit. For isolated capacity testing, set RATE_LIMIT=100000 in `.env`, use the stub profile, then run `python scripts/load_matrix.py` on the Docker host. The Locust E2E event includes queueing and polling, with warmup and graceful draining recorded. Compare one and three research workers, concurrency, cache settings, successful runs/s and failures. Do not interpret fast submit/poll responses as completed-run throughput.

## Scope and submission

This historical corpus is not current legal advice. Categories and certificates are caller declarations; document authenticity and technical quality require committee review. Regex guardrails have limited semantic coverage. A consortium, foreign or unknown category escalates. The supplied team has four SRNs although the brief suggests two or three; all supplied identities are retained. The selected institution tender was published through e-Wizard rather than CPPP.

Source is public at https://github.com/SasyakSubudhi/TenderScreen-Bid-Compliance. The final project package and comprehensive viva guide include reproducible commands, evidence definitions, measured limitations, incidents and ten demonstration flows. No external submission is performed.

## Final measured results and study documents

The corrected public source CI passed, and an anonymous clone built with `docker compose up --build -d` and served both example bids using fresh project volumes. Cached dependency layers were available. At ten concurrent users, successful E2E throughput was 0.437 runs/s with one research worker and 1.569 with three; p95 was 16 s and 6.5 s. First tested 30-second SLO misses were concurrency 20 and 60 respectively. These short measurements include graceful draining and are not steady-state capacity guarantees. The cache comparison showed no useful end-to-end improvement beyond noise.

The controlled 24-case-per-version stub comparison improved groundedness/faithfulness from 75% to 100%; complete-context precision fell from 100% to 91.25%. The separate actual CPU model batch verified 12/24 v1 and 2/24 v2 cases, with timeouts and shared breaker carryover. All failures are retained. Actual successful responses reported 61,116 input tokens and 5,811 output tokens; local provider fees exclude hardware/electricity and failed-call token work may be unknown.

* [Comprehensive project and viva guide](docs/Project_and_Viva_Guide.docx): 34 pages, 33 chapters, glossary, worked cases, code walkthrough and 70 viva answers.
* [Concise assignment report](docs/Assignment_Report.docx): 3 pages with architecture, four quality metrics, SLO/scaling/cache results, costs, incidents and limitations.
* [Requirement/evidence map](docs/STATUS.md) and [ten demonstrations](docs/DEMO.md).

When adding an alternate runtime profile, the configuration generator reuses existing private local API and Grafana credentials. This keeps the persisted Grafana database accessible when switching between stub and live inference. Preserve your private configuration files.
