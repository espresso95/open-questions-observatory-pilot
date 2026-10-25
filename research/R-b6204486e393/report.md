# Streamflow calibration transfer: an inconclusive station-support check

The frozen comparison could not be evaluated: only three of twelve selected evaluation stations had at least 30 recorded high-predicted-flow days, while the protocol required eight stations. The result is inconclusive. No stations were replaced and no thresholds were lowered.

## Question and source

Can error bars adjusted according to predicted river flow transfer to stations and later years held out from fitting that adjustment? [Gallant and Wilson](https://arxiv.org/html/2610.20947v1) report under-sized ensemble spread and propose flow-conditioned correction. Closely related [work on CAMELS-US](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7506823) already studies predicted-flow-stratified calibration and reports incomplete high-flow coverage recovery. That study was assessed through its primary-source search abstract; direct full-text access failed. This pilot makes no claim to invent flow-conditioned calibration.

The narrow question concerns transfer of a fixed normalized-residual calibration using the Canadian saved ensemble. It was not answered in the documented search coverage. Absence of a located answer does not certify novelty.

## Inputs and frozen design

Inputs come from [Gallant and Wilson's Zenodo software and data record 23142989](https://zenodo.org/records/23142989), version 1.1.0, licensed CC BY 4.0. Ten saved ensemble prediction files, observations and catchment areas were obtained through bounded range requests. No saved neural-network object or downloaded source script was executed. The whole-archive MD5 was not verified; selected members passed length and CRC checks, and retained range and derived input hashes identify the analysis inputs.

The deterministic sample consists of the 24 station identifiers with the lowest SHA-256 of `oqo-streamflow-v1:` followed by station ID. The first twelve form the posthoc calibration group; the remaining twelve form the evaluation group. All were used in the original regional LSTM training. The station split holds out the calibrator, not the original forecasting model.

Calibration uses 2006-2012 observations at its twelve stations. Evaluation uses 2013-2022 at the other twelve. Predictions are the ten-member mean and sample standard deviation. Observed discharge is converted from cubic metres per second to millimetres per day using catchment area. Missing, nonfinite and negative observations are excluded and counted; no replacements are imputed. Missingness may be seasonal and limits representativeness.

The baseline uses one 90th-percentile multiplier of absolute residual divided by ensemble spread. The conditional method uses three multipliers separated by the calibration predictions' 80th and 90th percentiles. Flow groups use predictions only. The primary endpoint was equal-station mean interval-score improvement on high-predicted-flow days, with at least 5% improvement, coverage within 0.05 of 0.90 and a positive lower paired catchment-bootstrap limit. Dependence precludes an exchangeable conformal coverage guarantee.

## What happened

The staged data contain 26,390 fitting rows and 34,011 evaluation rows with observations. The high-flow boundary was 5.22968054 mm/day, learned from calibration predictions. There were 1,649 evaluation rows above that boundary, but they were concentrated in very few stations.

| Evaluation station | Recorded high-flow days | Meets frozen minimum of 30 |
|---|---|---|
| 05BK001 | 3 | No |
| 05CA004 | 17 | No |
| 05CE011 | 0 | No |
| 05DF004 | 0 | No |
| 05DF007 | 0 | No |
| 07GB001 | 11 | No |
| 07GG002 | 6 | No |
| 07JF002 | 0 | No |
| 08CD001 | 88 | Yes |
| 08HF004 | 1,372 | Yes |
| 08LB024 | 18 | No |
| 08NK002 | 134 | Yes |

The required eight-station support was absent. The primary endpoint and its bootstrap interval were not evaluated. The fitted global and conditional multipliers are retained as fitting diagnostics, not evidence of successful transfer.

## Original failure and reporting amendment

Original frozen plan `4f62900ef554197cf0d602bc91fa396076fa073f4f8e633796a4b91ce5773b8f` raised an exception at the prespecified support gate. Both original attempts and a diagnostic run remain in the package. A later plan, `b6204486e393e4c61339560aaa92d79591744db95df6ca71b1466d7e23259be2`, changes only reporting: it returns this structured inconclusive result instead of an exception. Its amendment explicitly records the previously observed gate failure. Inputs, partitions, methods, thresholds and the success rule are unchanged. The original pre-outcome freeze is the scientific protocol; the amendment is not presented as an untouched preregistration.

## Validation and implications

Two fresh offline containers reproduced the structured inconclusive result exactly. A separate NumPy implementation matched calibration boundaries and multipliers with maximum difference zero, and independently counted the same three eligible stations. Execution stayed within the frozen one-CPU, 256 MiB, 120-second limit; the repaired primary run took less than a second.

The readiness assessment was too optimistic about support for the endpoint. Predictor-based station coverage could have been checked before dispatch without inspecting evaluation errors. Future qualification should require that support diagnostic. A revised experiment would need a justified new protocol, including how flow is compared across stations; the present result supplies no evidence that either calibration method transfers better.

The package contains the derived input, original and amended protocols, source code, failed-run receipts, successful reproductions, data rights and validation. Run `python3 reproduce.py` with Docker available to reproduce the amended result. This is AI-assisted retrospective research with no external scientific review or certified novelty.
