# Optimization suggestions — explicit permission required

Status: suggestions only. NOT approved for implementation or deployment.
Owner instruction: 2026-10-13, 09:08 Europe/Berlin.

The owner requested deployment of the already implemented current version, followed by documentation of the later optimization proposals. Do not introduce, enable, merge, or deploy any proposal below in any future edit without fresh, explicit owner permission covering that proposal. A general maintenance, bug-fix, deployment, or performance request is not permission to implement these proposals. Discussion, benchmark results, prototypes, and positive feedback are not implementation approval.

This restriction applies across tarous89/intel_mcp and tarous89/intel_agent_app.

## Current release versus unapproved proposals

The current implemented release is App PR #288 and MCP PRs #119 and #120. PR #120 removes redundant copies, bounds serialization, preserves the existing full-workspace fallback through temporary-file spooling, and serializes existing heavy operations. It does not implement progressive category loading. Those existing changes are distinct from the proposals below.

## Proposals requiring permission

1. Requested-category-first / progressive workspace: return the first ten basic results before all four tables are ready; prepare the other categories automatically in the background.
2. Progressive details: fill detailed rows after the basic table appears; introduce automatic tab/detail readiness updates, progress indicators, or clicked-tab priority.
3. Durable resumable stages: persist partial category/job state, resume incomplete background jobs, and replace full reconstruction with stage-level recovery.
4. Additional cache offloading: move retained source selections or completed category caches out of MCP RAM; change cache placement, retention, eviction, or related infrastructure.
5. Additional result/fingerprint reuse: cache and reuse prepared category outputs or fingerprints across stages/requests beyond the existing implementation, with new invalidation rules.
6. A background-work scheduler for the above stages, including automatic work ordering, per-user fairness, prioritization, or new background status/polling behavior.

Do not bundle these proposals into unrelated edits or quietly implement them as a follow-up optimization. Obtain explicit approval first, then document the approved scope and date.

## Investigation evidence, not production guarantees

A local prototype used 420 trials, 5,040 sites and 5,040 investigators. Compared with the already optimized code, first-category computation was approximately 5.5 seconds versus 0.1 seconds; full-process peak RSS was approximately 179 versus 156 MiB; total preparation/serialization was approximately 7.2 versus 8.6 seconds. Retaining completed stages in RAM instead of releasing them reached approximately 200 MiB. Final category contents were compared for equality.

These are isolated synthetic measurements, excluding database searches, real remote storage/network, and ChatGPT host-opening latency. They are not promises of production timing or capacity. The prototype is not included in product source.

Any approved future design must preserve a frozen source snapshot, full-cohort ranking for the initial ten, stable ordering/identity, access controls and evidence accuracy. It must distinguish partial readiness from verified persistence, avoid incomplete reports, bound server-wide concurrency, and surface stage failures honestly.
