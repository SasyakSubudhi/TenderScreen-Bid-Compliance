# Ten demonstrations

1. Start: run RUN_DEMO.cmd or generate runtime configuration and use the matching Compose up --build command. Show health and a complete HTTP run. Clean-source startup is separately recorded.
2. Agent workflow: submit examples/valid.json; show the run ID, research tools, persisted handoff and verifier. Identify containers with hostname plus PID, not PID alone.
3. Difficult case: submit examples/startup_conflict.json. Show the INR 2.4 million five-year threshold, modifying startup policy, dual citations and committee escalation.
4. Corpus: run python -m app.corpus twice; inspect 128 chunks and repeat reuse. Use --reembed-chunk with a real ID; show one updated vector and 127 retained.
5. Quality comparison: show all four metrics in evaluation.json for 24 fixed cases per variant. Discuss context precision versus evidence coverage. Show actual live_evaluation.json degradation separately.
6. Interface and guardrails: show /docs, malformed JSON/schema quarantine, obvious prompt injection rejection before agents, unknown-category escalation and feedback.
7. Verification failure: run the citation-tampering and missing-policy repair tests. Show bounded alternate retrieval and final safe abstention for unsupported findings.
8. Operations: open Grafana and Jaeger. Show per-agent steps/latency, container resources and traces connecting API/research/verification. Prometheus targets must be healthy.
9. Load and scaling: show load_matrix.json and Locust E2E CSV rows for one versus three workers at common concurrency. Discuss the unchanged 30-second SLO, first tested misses and failures. Distinguish successful run RPS from HTTP polling rates.
10. Fault and recovery: use the isolated stub procedure in RUNBOOK.md; show retry events, breaker opening, explicit incomplete result, restored configuration and a new verified run. Compare measured cache runs and actual model tokens/cost scope.

The base profile is a delayed deterministic stub. The live profile is actual local inference and semantic embeddings; do not mix their claims. Full project/viva details are in the accompanying DOCX.
