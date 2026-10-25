---
title: "Can exact attainment witnesses for the proposed maximal prefix-reversal rows be found beyond n=100?"
description: "A bounded AI-assisted investigation with a frozen protocol and retained limitations."
question_id: Q-MATH-002
run_id: R-1afd1ba41d69
disciplines: [mathematics]
---

# Finite prefix-reversal witnesses beyond the published computation range

Nine selected even values of k have exact attainment witnesses beyond n=100. Across the nine tested rows, 513 triples generate every permutation and 37 generate a proper subgroup. All 550 classifications passed an independent SymPy check. This establishes the listed finite cases; the general conjecture remains unresolved.

## Question and prior work

Imagine a list of n distinct items. A prefix reversal flips the order of the first q items. We allow only three fixed reversal lengths: n, m and k, with 2 <= k < m < n. Which triples allow every possible rearrangement?

[Blanco and colleagues](https://arxiv.org/html/2511.16959v2) report computations through n=100 and state Conjecture 5: for fixed k, the largest number of successful middle reversal lengths m is k+1 when k is even and (k+1)/2 when k is odd. Their broader asymptotic count is a separate conjecture. A [newer paper](https://arxiv.org/html/2610.30892v1) proves earlier Conjectures 2-4; those answered claims were excluded from this pilot. The inspected author repository contains no computation beyond n=100. The documented search located no answer to these selected rows, but novelty has not been independently certified.

Published generating families and shift theorems already cover some individual triples. This pilot supplies a fully retained certificate set for the listed finite rows. Independent assessment of whether those complete row results add new mathematics remains outstanding.

## Frozen finite search

The plan was frozen at 2026-10-25T18:58:12+00:00 under SHA-256 `1afd1ba41d69f707ff6ffb157e0667a989e80147979442819f7bf7b3be57f799`. The machine-readable plan is authoritative for its exact timestamp.

For k=48,50,...,64, consider in ascending order the first three prime offsets p>k+1 satisfying n=k+p>100 and n=3 modulo 4. Test every middle length m from k+1 through n-1. Stop that k after a completely classified row contains k+1 successful triples. This is a finite witness search with a legitimate prespecified stopping rule. Every attempted triple is retained, including obstructions and unknown classifications. No unknown classification is counted as failure or success. In this run, the first row for each k attained the proposed count, so no second or third row was attempted.

## Results

| Short reversal k | List length n | Successful middle lengths |
|---|---|---|
| 48 | 107 | 49 |
| 50 | 103 | 51 |
| 52 | 111 | 53 |
| 54 | 115 | 55 |
| 56 | 115 | 57 |
| 58 | 119 | 59 |
| 60 | 127 | 61 |
| 62 | 135 | 63 |
| 64 | 131 | 65 |

All 550 tested triples were classified. The complete results retain each triple and its certificate. These finite witnesses establish the attained row counts at the listed n. They do not prove an upper bound over all n or settle the conjecture for every k.

## How the certificates work

A successful certificate checks that the three reversals act primitively, that at least one is an odd permutation, and that an explicit finite word in those reversals produces a prime-length cycle fixing at least three points after a recorded power. [Jordan's theorem](https://arxiv.org/abs/1209.5169) then establishes that the generated group is the full symmetric group. Random choices only locate a candidate word; acceptance checks that word exactly. Proper-subgroup certificates use an explicit orbit, invariant block partition, or parity obstruction.

Small groups were also checked by exhaustive enumeration. A separate implementation using pinned SymPy 1.14.0 verified all 513 success certificates and 37 obstructions, using deterministic primitivity tests and its own permutation multiplication and exponentiation. It did not import the primary adapter.

## Reproduction, resources and limits

Two fresh offline containers produced identical structured results. The primary computation took about 3.6 seconds and peaked near 14 MiB resident memory. The frozen limit was 120 seconds, one CPU and 256 MiB, with an unprivileged user, read-only root filesystem, no network and no host mounts. The independent certificate check took about 1.1 seconds.

The package includes the exact plan, analysis, certificates, resource receipts, validation and a reproduction command. Run `python3 reproduce.py` with Docker available. The image is pinned by digest and the primary computation uses the Python standard library.

This is AI-assisted finite mathematical research. No external scientist has reviewed the argument or certified its novelty. A human mathematical review should examine the formalization, primitivity checker, certificate verifier and relationship to existing generation theorems before making a broader scientific claim.
