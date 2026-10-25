# Bounded next-phase runtime

The shared path is `retrieval.Broker` -> source snapshots -> `assessment.assess/admit` -> `experiment.freeze` -> `experiment.execute/reproduce` -> independent validation -> `export.run`. Formal and empirical adapters use the same frozen-context runner. A failed scientific eligibility rule is retained as an inconclusive outcome; it is not repaired by lowering the threshold.

New streamflow freezes now run a predictor-only station-support gate before creating a plan. It uses the same frozen thresholds and observation-availability mask without reading evaluation errors. Existing historical plans and their failures remain unchanged; they can still be reproduced. A reporting amendment is not an exemption for a new investigation.

`config/providers.json` bounds public acquisition. The setup allocation was raised from 50 MB to 250 MB to selectively obtain saved Canadian ensemble predictions and observations, avoiding the 400 MB whole archive and all model deserialization. The measured download ledger is private. Trial acquisition has a separate 1 MB/day, six-request limit. Paid providers and cloud-model calls remain disabled.

The seven-day supervisor uses SQLite transactional claims, immutable job identities, attempt counts, leases, conservative post-crash resource accounting, bounded retries and dead letters. Only fixed integrity checks, approved frozen reproductions, a known public metadata probe, backups and fault exercises are registered. Source text cannot introduce a command or a new job kind. Research containers receive no network, host mounts or publication credentials.

The launch agent is `org.oqo.pilot.supervisor`. It uses the current non-root account and the isolated `oqopilot` VM. It does not qualify a dedicated OS account, physical reboot, FileVault recovery or new-question admission without review. `caffeinate -i` prevents idle system sleep during the bounded trial. Successful termination at its seven-day boundary stops the assertion; launchd restarts unexpected failures. A daily native Codex heartbeat checks actual state and records, rather than keeping a chat process asleep for seven days.

Inspect local state with:

```sh
python3 -m engine.supervisor status
launchctl print gui/501/org.oqo.pilot.supervisor
```

The user can stop the service with `launchctl bootout gui/501/org.oqo.pilot.supervisor`. Stopping it interrupts qualification and must be reflected in the event history. A service listing or one successful heartbeat is not evidence of seven-day operation.

The private disclosure candidate is generated from an explicit allowlist. It includes scoped question records, short quotations, citations, frozen plans, analysis, results, verification code and permitted derived data. It excludes original source full texts, caches, SQLite, the design document and private human-review records. It has no network upload capability. `require_disclosure_approval` binds permission to the exact current bundle hash. Public science is registered under detached release manifests; trusted code maintenance preserves historical scientific files.

Schema v2 permits questions with no research attempt and a plain scope description, while retaining independent literature, feasibility, research, validation and publication states. Existing v1 records remain unchanged and supported. Admission still requires exact source evidence, a documented literature assessment and every execution gate. Readiness scores alone never authorize dispatch.
