# Genuine incidents and lessons

1. Some direct policy hosts failed or returned 403. An alternative PDF had no useful text layer. Official text-layer copies were obtained from government mirrors/compendia, and URLs, fingerprints and page mappings were preserved. Every curated quotation is tested against its source page.
2. Windows FAISS initially failed native DLL initialization. The bundled Python runtime, required native access and OMP_NUM_THREADS=1 recovered execution; the final suite passed 23 tests on Windows and Linux.
3. WSL Docker package downloads stalled on bridge DNS. Host-network builds reached the package index and completed. Runtime configuration exposes a build-network choice.
4. WSL idle shutdown stopped containers with exit 255. They were not recorded as successful runs. Restart policies and foreground WSL/Compose operation recovered the stack.
5. Long contexts and CPU model inference caused deadlines; an early smaller model also invented a policy identifier. Compact observations and exact bounded verification improved functional examples, but the full real-model batch still degraded. In v2 the shared breaker opened and later cases abstained quickly. All 48 observations are retained. This is not a valid prompt-only causal estimate.
6. The first Prometheus resource target used an obsolete cAdvisor name. The resource exporter was added to the default trusted local stack, the target was corrected and Prometheus reloaded; all eight targets were subsequently healthy.
7. A root manifest ignore pattern also excluded the corpus provenance manifest on the case-insensitive Windows checkout. It was anchored to the repository root, the corpus manifest was committed, and the corrected public source CI passed.
8. Context relevance was initially computed only over selected citation IDs. The scorer was corrected to use ALL retrieved contexts, including repair. Frozen live results were rescored from persisted traces without rerunning or excluding cases.

See evidence/ for raw functional checks, actual token reports, failed live cases, indexing measurements, load records and container test logs. Failures are preserved rather than converted into successful claims.
