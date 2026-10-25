---
title: "Can calendar information improve spring ENSO forecasts?"
description: "A frozen, reproducible pilot on a question with no answer located in the documented search."
---
# Can calendar information improve spring ENSO forecasts?

The frozen decision rule was not met. This pilot does not demonstrate the proposed robust improvement; the general research question remains open.

This is a retrospective research pilot, with no answer to the exact comparison located in the documented English-language search. Seasonal ENSO forecasting is well studied; neither a new forecasting algorithm nor independent novelty is claimed. The wider spring predictability barrier is unresolved by this experiment.

## Question and motivation

Does a fixed season-aware direct six-month AR6 forecast lower February–April initialized Niño 3.4 RMSE by at least 5% against both persistence and an otherwise comparable non-seasonal AR6, with positive paired intervals under all prespecified block lengths?

Gan and colleagues' [2026 preprint](https://arxiv.org/html/2601.02050v1) identifies persistent seasonal forecast limitations and suggests richer predictor information. This pilot tests a narrower statistical question about calendar effects. It does not reproduce their deep-learning model or test their physical-variable proposal. [Related 2026 work](https://www.sciencedirect.com/science/article/pii/S0169207026001019) already studies seasonal score-driven forecasts through 2024; its methods, index vintage, inputs and evaluation window differ. Full-text access to that study failed, limiting the literature assessment.

## Data and fixed method

Use [NOAA CPC ERSSTv5 monthly Niño 3.4 anomalies](https://psl.noaa.gov/data/timeseries/month/Nino34_CPC/) in °C relative to 1981–2010. The cached snapshot has 945 valid months, from 1948-01 through 2026-09. No missing values were imputed.

Training uses 769 examples with target months ending by 2014-12. Holdout forecasts start in 2015-01; the last available issue is 2026-03, targeting 2026-09. At each issue date the model sees only that month's anomaly and the preceding five months. Forecasts are direct six-month forecasts; parameters are fitted once and never updated from holdout outcomes.

Both regressions use a fixed ridge penalty of 1 on all coefficients except the intercept. The season-aware model adds sine/cosine of issue month and their interactions with the latest anomaly. No hyperparameter search or subsequent outcome-driven model changes occurred. Persistence predicts the latest observed anomaly. Two fitted models and one fixed baseline are the entire analysis family.

The plan was frozen internally at 2026-10-25T17:25:33+00:00; it is not an external preregistration. This is pseudo-out-of-sample evaluation of a single revised data vintage. Historical release delays and data revisions are not reconstructed, so it is not an operational forecast verification.

## Primary results

The primary subset comprises forecasts initialized in February, March or April, with only targets available by the September 2026 cutoff. This operational definition differs from some published spring-barrier definitions.

| Forecast | RMSE (°C) | MAE (°C) | Forecasts |
|---|---:|---:|---:|
| Persistence | 1.0537 | 0.8863 | 35 |
| Non-seasonal AR6 | 0.8216 | 0.6532 | 35 |
| Season-aware AR6 | 0.8240 | 0.6581 | 35 |

Against persistence, relative RMSE skill is 21.80%. Positive values favor the season-aware model.

- 2-year blocks: descriptive 95% interval 2.21% to 42.47%.

- 3-year blocks: descriptive 95% interval 4.06% to 37.43%.

- 4-year blocks: descriptive 95% interval 12.53% to 35.57%.

Against non-seasonal AR6, relative RMSE skill is -0.29%. Positive values favor the season-aware model.

- 2-year blocks: descriptive 95% interval -7.05% to 3.41%.

- 3-year blocks: descriptive 95% interval -6.16% to 2.91%.

- 4-year blocks: descriptive 95% interval -5.36% to 2.30%.

The prespecified rule requires at least 5% lower RMSE against both baselines and a positive lower skill endpoint for every 2-, 3- and 4-year paired circular block bootstrap. It does not require a favorable result to count the pilot as a completed investigation. Secondary all-month and other-month results and every prediction are in results.json.

## Validation and limits

The identical structured output was reproduced in two fresh Linux containers from a digest-pinned Python image. Each run had a 45-second wall limit, 128 MiB memory, one CPU, no network, no host mounts, a read-only root filesystem and an unprivileged user. Runs took 0.279 and 0.249 seconds. Probes checked root write denial, external network denial, missing host home/socket and absence of credential environment variables.

Bootstrap uncertainty uses paired circular blocks of calendar years, 2,000 replicates per block length and fixed seeds. There are few ENSO cycles; the intervals are descriptive finite-record uncertainty and can miss slower dependence or nonstationarity. The frozen 5% threshold is an engineering decision rule, not a physical discovery threshold. No test here establishes future forecast skill or causation.

Computational reproduction checks repeatability. It does not establish scientific adequacy. No independent scientist, expert reviewer or external peer reviewer has reviewed this pilot. Publication remains a private draft pending human disclosure approval.

## Reproduction and attribution

Download the reproducibility package from this page. It contains the exact data snapshot, plan, source code, pinned runtime, results, checksums, literature search and reproduction command. Full source-paper HTML, private logs and SQLite are excluded.

Data: NOAA Climate Prediction Center; provided by NOAA Physical Sciences Laboratory, Boulder, Colorado, USA. The source paper is Gan et al., arXiv:2601.02050v1 (CC BY 4.0). This report and analysis are AI-assisted, with no endorsement by NOAA or the paper's authors.
