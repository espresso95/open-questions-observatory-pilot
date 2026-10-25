# Open Questions Observatory — end-to-end pilot

This is an agent-assisted research pilot of the October 25, 2026 design. The user requires a question with no known answer in the documented literature search. A previously proposed, already answered solar-cycle control was rejected before data acquisition or analysis.

The selected question tests whether a small season-aware model improves six-month Niño 3.4 forecasts initialized in February–April over both persistence and a non-seasonal model on the 2015–2026 observational record. The parent problem is the still unresolved ENSO spring predictability barrier. The exact bounded comparison has no answer located in the recorded search; that is not a proof of novelty or universal absence of an answer.

The pipeline preserves source passages, records coverage and related work, freezes the protocol before running the analysis, enforces local resource and network limits in a Linux VM, repeats computation in a fresh container, and generates a static local review site and reproducibility bundle. Private state and snapshots live in `.private/`, excluded from Git.

No claim of scientific resolution, independent review, autonomous cross-disciplinary discovery, or production readiness is implied. Publication requires human approval of an exact bundle digest.

## Result

The frozen rule was not met. On 35 spring-initialized holdout forecasts, RMSE was 0.824°C for season-aware AR6, 0.822°C for ordinary AR6 and 1.054°C for persistence. The seasonal extension improved on persistence but did not improve on the stronger statistical comparator. Paired uncertainty intervals include no seasonal advantage over ordinary AR6. This is a useful negative finding for the specified model and data window; the wider scientific problem stays open.

## Reproduce the pipeline

Use Python 3.12 or newer, Node 24 and Docker backed by an isolated Linux VM. The pilot was run on macOS arm64 with a dedicated Colima profile. It does not use the user's broken/stopped default profile.

```sh
colima start -p oqopilot --cpus 2 --memory 2 --disk 8 --mount none --ssh-config=false --activate=false --template=false --runtime docker --vm-type vz
docker --context colima-oqopilot pull python@sha256:35caba83af2fe6da9a5d922f9b0156f21d1246a48278c58a08bd253303ba42e8
python3 -m engine.pilot run
```

The first run retrieves the exact approved URLs. Later runs validate and reuse snapshots and completed results by plan identity. `prepare` freezes without running. The original freeze and failed build attempt remain in the private SQLite event history; repairing the builder did not alter the scientific analysis or plan. No source data or model output was inspected before freezing the computational plan, apart from literature information used to formulate the hypothesis.

The analysis itself uses only the Python standard library inside a digest-pinned container. Host verification uses the separate pinned dependencies in `config/verification-requirements.txt`:

```sh
uv venv --python python3.12 .venv
uv pip install --python .venv/bin/python -r config/verification.lock
.venv/bin/python -m engine.verify
python3 -m unittest discover -s tests -v
python3 -m engine.pilot run
```

The final command incorporates independent verification and figures while reusing the completed scientific run. The report is regenerated from structured results. Inspect `review-bundle/manifest.json` for the current disclosure digest.

## Build and view

```sh
npm --prefix site ci --no-audit --no-fund
npm --prefix site run build
python3 -m engine.check_site
python3 -m http.server 4321 --bind 127.0.0.1 --directory site/dist
```

Open `http://127.0.0.1:4321/`. Question pages, a Markdown research report, source records, JSON exports, figures, search and a reproduction ZIP are static files. The website works without the research VM. Stop the dedicated VM after research with `colima stop -p oqopilot`.

## Reproduce the reader's package

Download the ZIP from the report page, extract it, change into its `research/R-…/` directory and run:

```sh
DOCKER_CONTEXT=colima-oqopilot python3 reproduce.py
```

Any Docker context backed by Linux is acceptable; omit the environment variable if the current context is suitable. The runner verifies all artifact checksums, builds from the pinned runtime and compares fresh structured output with the saved result. Downloading the runtime needs network; the research container does not.

## Verification and limits

- Two original executions produced identical results in fresh restricted containers.
- Independent NumPy augmented least-squares and separate feature construction agreed with predictions to about 10⁻¹⁵.
- Focused tests cover source quotation integrity, rights, unknown gates, scientific-status escalation, unsafe URLs, export secrets/symlinks, content-bound approval, malformed dates and numerical pivoting.
- Browser checks exercise search, discipline filters, question/report navigation, mobile layout and the actual download.
- Static checks inspect every internal page/asset/download link and ensure private state is absent from the build.

Question formulation and literature assessment are agent-assisted. The exact-comparison search is limited; novelty is unverified. Historical input revisions and release delays are not reconstructed. There is no installed scheduler, recurring task, paid call, external outreach, production deployment, seven-day reliability qualification or external scientific review. See `policies/pilot-boundaries.md` and the report for the precise boundaries.

## Publication gate

Design section 12 requires local human review of the exact export before any public PR or push. `engine.policy.require_disclosure_approval` rejects absent approval and any content change after approval. No public upload is part of the local pilot command. A public publishing broker and CI workflow remain subject to the user's review of this concrete result.

Data credit: NOAA Climate Prediction Center; provided by NOAA/OAR/PSL, Boulder, Colorado, USA, from https://psl.noaa.gov/. NOAA data is identified separately and is not claimed as project-owned material. Source paper: Gan et al., arXiv:2601.02050v1, CC BY 4.0. The approved source snapshots and rights evidence remain private; full third-party papers are excluded from the export.
