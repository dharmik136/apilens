# APILens Delivery Operating Model
### An end-to-end lifecycle framework for improvements and new features — idea to production and back

---

## 0. North Star — the philosophy behind the framework

Four principles govern everything below. They exist because of things that actually happened in this codebase, not because a consultant said so.

**1. Risk-proportional rigor.** Not every change deserves every gate at full weight. A copy fix and a change to the SDK wire format are not the same species of work. Every phase below scales its depth by a **blast-radius tier** (defined in Phase 4). Applying maximum process to everything guarantees the process gets ignored; applying it proportionally makes it survivable for a small team.

**2. Reversibility bias.** Prefer the version of a change that is cheap to undo. The SDK already contains the house pattern: `APILENS_CAPTURE_SPANS` is an env-var kill-switch where the environment always wins over code-level config and can only turn the feature *off*, never silently back on. Every new feature should ship with its equivalent. A rollback plan written after the incident starts is not a plan; it's improvisation under adrenaline.

**3. Evidence over opinion — and shipping is not done.** The Traffic page's endpoint table showed "No endpoint activity" for *every project, always*, because a query silently required a Postgres row that nothing in the live app could ever create. It passed code review. It would have passed most unit tests. It was caught only when someone ran the actual product against seeded data. That is why **post-deployment validation is a distinct gate**, not a nice-to-have.

**4. Most ideas should die, and die cheaply.** This framework has **five explicit go/no-go gates** (G1–G5). Their purpose is to kill work at the cheapest possible moment. A healthy funnel rejects or defers most ideas at G1/G2, where the sunk cost is a one-page brief — not at G4, where it's three weeks of engineering. A gate that always says "go" is decoration.

---

## 1. Quick Reference

### The five go/no-go gates

| Gate | When | Question it answers | Outcomes | Decider |
|---|---|---|---|---|
| **G1 — Research** | End of Phase 1 | Is this problem real, painful, and ours to solve? | Go to discovery / Park with reason / Kill | Product owner |
| **G2 — PRD** | End of Phase 3 | Should we build this, now, in this shape? | Build / Defer / Reject / Spike first | Product owner + tech lead, jointly |
| **G3 — Design** | End of Phase 5 | Is this the right way to build it, and is the blast radius acceptable? | Approve / Revise / Escalate scope back to G2 | Tech lead (+ second reviewer for Tier 3–4) |
| **G4 — Pre-deployment** | End of Phase 9 | Are we ready to ship — including ready to *unship*? | Deploy / Hold | Tech lead; requires signed-off rollback checklist |
| **G5 — Post-deployment** | During Phase 10 | Is it actually working in production, against real traffic? | Promote / Hold-and-watch / Rollback | Owning engineer + tech lead |

A "no" at any gate is a success of the process, not a failure of the idea's author. Record the kill reason in one line — future-you will re-encounter the same idea and want to know why it died.

### The twelve phases

| # | Phase | Owner | Key deliverable |
|---|---|---|---|
| 1 | Research & Opportunity Framing | Product owner | Opportunity brief (1 page) → **G1** |
| 2 | Requirement Discovery | Product owner + tech lead | Requirements doc (functional + NFR) |
| 3 | PRD Creation | Product owner | Approved PRD → **G2** |
| 4 | Impact & Feasibility Analysis | Tech lead | Blast-radius map + feasibility score |
| 5 | Architecture & Dependency Review | Tech lead | ADR / design doc → **G3** |
| 6 | Implementation Planning | Owning engineer | Sliced, sequenced task plan |
| 7 | Coding Workflow | Owning engineer | Merged, reviewed, CI-green PRs |
| 8 | Testing Strategy | Owning engineer | Tiered test evidence |
| 9 | Deployment Planning | Owning engineer + tech lead | Deploy + rollback runbook → **G4** |
| 10 | Post-Deployment Validation | Owning engineer | Validation report → **G5** |
| 11 | Rollback Preparedness | Owning engineer | Kill-switch + reversibility proof (input to G4) |
| 12 | Continuous Improvement | Whole team | Retro with owned actions; loop to Phase 1 |

### Refine / Rollback / Scrap — condensed

| Situation after release | Branch |
|---|---|
| Core hypothesis holds; execution has fixable defects; guardrails intact or mildly degraded | **REFINE** forward |
| Guardrail breached hard, or defect severity high, or forward-fix > ~1 day while users are hurting | **ROLLBACK** now, refine later |
| The *assumption* was wrong (users don't want it / signal was noise), not the execution | **SCRAP**; return to Phase 1 with the learnings |

Full decision tree with numeric triggers: §15.

---

## 2. Phase 1 — Research & Opportunity Framing

**Why it exists.** The scarcest resource is engineering weeks. Work that starts from an unvalidated opinion ("users probably want X") spends that resource on a coin flip. This phase converts "someone had an idea" into "we have evidence of a problem worth solving" — or kills it for the price of a page of writing.

**What to mine (in order of signal quality):**
1. **Your own telemetry about APILens usage** — which dashboard pages get visited, which API endpoints customers actually query, where sessions abandon. You build an observability product; instrument your own.
2. **Support requests and direct user conversations** — verbatim quotes, not paraphrases.
3. **Existing artifacts already in this repo** — the completed 10-journey Playwright UX audit (`product-playwright-deep-dive/`) contains a findings backlog of real, unaddressed gaps. It is a signal mine that costs nothing to re-read. Check it before declaring a gap "newly discovered."
4. **Competitive gaps** — what Apitally/Datadog/Moesif offer that customers ask about. Weakest signal alone; useful as corroboration.

**Deliverable: the Opportunity Brief (one page, hard limit).**

```
OPPORTUNITY BRIEF
Title:
Problem hypothesis:      (one sentence: WHO has WHAT pain, HOW often)
Signal sources:          (tickets #, telemetry query, interview notes, audit item)
Evidence strength:       Strong / Moderate / Anecdotal   (be honest)
Who is affected:         (segment + rough count/percentage)
Strategic fit:           (does this serve the core "API observability" thesis?)
Score:                   Reach(1-5) × Pain(1-5) × Fit(1-5) × Confidence(0.2-1.0) = ___
What we are NOT claiming: (explicitly note what the evidence does not show)
Recommendation:          Proceed to discovery / Park / Kill — and why
```

**Gate G1 — go/no-go mechanics.** The product owner decides, using the score as a forcing function, not an oracle. Practical thresholds for a small team: score ≥ 40 → discovery; 20–40 → park with a re-review date; < 20 → kill and log the reason. Confidence multiplier matters most: a Reach-5/Pain-5 idea backed only by one anecdote (confidence 0.2) scores 25× fit — it *parks*, pending better signal, rather than jumping the queue.

**Best practices.**
- Timebox research to days, not weeks. If evidence isn't findable quickly, that itself is signal (confidence is low).
- Write the kill reason down. A one-line graveyard (`ideas-graveyard.md`) prevents relitigating the same idea quarterly.
- Never let the person most excited about an idea also be the only one scoring its confidence.

---

## 3. Phase 2 — Requirement Discovery

**Why it exists.** An opportunity says *why*; requirements say *what, testably*. Skipping this phase produces PRDs where "success" is undefined and engineers back-fill requirements from their own assumptions mid-implementation — which is how scope silently doubles.

**Non-functional requirements are first-class citizens here, not an appendix.** For APILens specifically, every discovery pass must explicitly answer:
- **Data volume:** what does this do to ClickHouse row counts / query load at 10× current traffic?
- **Latency:** what dashboard or API p95 budget does this consume?
- **SDK wire-format compatibility:** does this require the ingest payload to change? (If yes, blast radius jumps to the maximum tier immediately — see Phase 4 — because the SDKs run inside *customer* production apps and cannot be force-upgraded or rolled back by us.)
- **Authz surface:** does OPA need a new policy? Remember OPA is configured **fail-open** — a missing policy doesn't deny access, it allows it. A new endpoint without an explicit policy check is a silent authorization hole, not a 403.

**Deliverable: Requirements doc** — functional requirements as user stories with acceptance criteria ("Given/When/Then"), NFRs with numbers, explicit out-of-scope list, and open questions tagged *blocking* vs *non-blocking*.

**Owner.** Product owner drives; tech lead must co-review because NFRs die when written by someone who can't estimate their cost.

**Discovery Definition of Done — checklist:**
- [ ] Every functional requirement has a testable acceptance criterion
- [ ] Data-volume, latency, wire-format, and authz questions each have a written answer (even if "unaffected")
- [ ] Out-of-scope list exists and names at least the two most tempting adjacent features
- [ ] Every open question is tagged blocking / non-blocking
- [ ] The affected user journey is written down end-to-end (or referenced from the UX audit)

---

## 4. Phase 3 — PRD Creation → Gate G2

**Why it exists.** The PRD is the contract between "what we agreed to build" and everything downstream. Its most underrated sections are **non-goals** and **rollback sketch** — the first prevents scope creep, the second forces reversibility thinking before a line of code exists.

**Deliverable: the PRD.**

```
PRD: <feature name>                                   Status: Draft / In review / Approved
1. Problem statement        (from the opportunity brief, refined)
2. Goals                    (max 3, each mapped to a metric below)
3. Non-goals                (explicit — "we will NOT also...")
4. User stories + acceptance criteria
5. Success metrics
   - Leading  (visible in hours/days): e.g. feature adoption rate, error rate of new path
   - Lagging  (visible in weeks):      e.g. retention delta, support-ticket reduction
   - Guardrails (must NOT degrade):    e.g. dashboard p95, ClickHouse CPU, ingest throughput
6. Rollout sketch           (flag? dark ship? staged %? — one paragraph)
7. Rollback sketch          (what's the kill-switch? is any data change reversible?)
8. Open questions           (blocking vs non-blocking)
9. Out of scope
```

**Guardrail metrics deserve emphasis:** a feature that hits its success metric while blowing a guardrail (new alerts feature ships, dashboard p95 doubles) is a **failure**, and the PRD must say so in advance so nobody argues it after launch.

**Gate G2 — go/no-go mechanics.** Product owner and tech lead decide *jointly* — product can't overrule "this is technically reckless," engineering can't overrule "nobody wants this." Four outcomes:
- **Build** — proceeds to Phase 4.
- **Defer** — right idea, wrong quarter; gets a revisit date.
- **Reject** — evidence didn't survive scrutiny; log to the graveyard.
- **Spike first** — a blocking open question needs a timeboxed technical investigation (≤ 2–3 days) before the gate re-runs.

**"Final enough" to pass G2** does not mean zero open questions. It means **zero open questions whose answer could change the go/no-go decision.** Everything else can be resolved during design.

---

## 5. Phase 4 — Impact & Feasibility Analysis

**Why it exists.** This is where "what could this possibly touch?" gets answered systematically instead of by vibes. Two real incidents in this codebase are the argument for it:

> **Incident: the twenty routes.** Twenty separate Next.js API routes each independently proxied requests to Django, and *all twenty* were missing the same token-refresh logic that one shared helper already implemented elsewhere. A fix applied to "the place I changed" would have silently left nineteen copies broken. The lesson: impact analysis must ask **"who else has this same pattern?"**, not just "what file am I editing?"

**Deliverable 1: the Blast-Radius Map.** Walk every layer explicitly; write "unaffected" where true — the writing-it-down is the audit:

| Layer | Touched? | How | Severity |
|---|---|---|---|
| Postgres schema (projects/apps/users/memberships) | | | |
| ClickHouse schema or query load (`api_requests`) | | | |
| Django API surface (routers/schemas) | | | |
| Next.js BFF proxy layer (`app/api/**`) | | | |
| Frontend UI | | | |
| Ingest service (FastAPI) | | | |
| **SDK wire format (Python/TS)** | | | **Any "yes" here = Tier 4 automatically** |
| OPA policy (remember: fail-open) | | | |
| Scheduled jobs / new infra dependencies | | | |
| Docs / onboarding | | | |

**Blast-radius tiers** (drive rigor everywhere downstream):
- **Tier 1** — cosmetic/copy/one-component UI. Reversible in minutes.
- **Tier 2** — internal logic, single service, no contract change.
- **Tier 3** — cross-service or customer-visible behavior; schema changes; new dependencies.
- **Tier 4** — SDK wire format, auth/authz, billing, destructive data migration. Maximum rigor, always.

**Deliverable 2: the "who else" audit.** Grep for the pattern, not the file. Use `/graphify` (the repo's codebase-structure skill) to answer "what imports this / what else calls this endpoint / where else does this pattern appear." Fifteen minutes here is cheaper than the twenty-routes incident.

**Deliverable 3: feasibility score.** Complexity (1–5, inverted), Capacity fit (1–5), Risk (1–5, inverted), Confidence (1–5) → average. Worked example: anomaly-detection alerts = Complexity 3 (new scheduled job, baseline math) → 3; Capacity 4; Risk 3 (new infra dependency, but zero SDK impact) → 3; Confidence 4 → **3.5 = feasible, schedule normally.** Below 2.5: don't start without descoping or a spike.

**Decision mechanism.** Tech lead calls Go / Defer / Reject / Spike. Crucially, **feasibility is re-scored at every later gate**, not decided once — a design review that discovers the "simple" change needs a Tier-4 migration must bounce back here, and that bounce is the system working.

---

## 6. Phase 5 — Architecture & Dependency Review → Gate G3

**Why it exists.** Design mistakes are 10× cheaper to fix on paper than in a migration that already ran in production. This phase also creates the *decision record* — six months later, "why is it built this way?" has an answer that isn't archaeology.

> **Incident: the dead layer.** After the product pivoted from flat "apps" to "projects contain apps," the old backend router, its 20 matching frontend proxy routes, four UI components, and 26 client methods stayed mounted-but-unreachable for months. Nothing decommissioned them because no design ever included a decommission step. Retiring the old path is an explicit design deliverable, not something that happens by osmosis.

**When is a design doc mandatory?** By tier: Tier 1 — none. Tier 2 — a paragraph in the PR description. Tier 3 — a lightweight ADR. Tier 4 — full ADR + data-flow diagram + a named second reviewer, no exceptions. Anything touching the ingest wire format or auth is Tier 4 by definition.

**ADR template:**

```
ADR-NNN: <title>                          Status: Proposed / Accepted / Superseded
Context:        (the problem and constraints — 1 paragraph)
Decision:       (what we're doing — 1 paragraph)
Alternatives:   (2-3 considered, one line each on why rejected)
Consequences:   (what gets harder/easier; new dependencies; what must be decommissioned)
Rollback story: (how this is undone if wrong)
Blast tier:     1/2/3/4
```

**Reviewing the two highest-risk change types:**

*ClickHouse schema changes* — always **expand/contract**, never in-place mutation: (1) additive migration first (new column/table, old untouched); (2) code that reads both shapes; (3) backfill; (4) cut reads over; (5) drop the old shape in a *separate, later* release. This repo's dual-migration ClickHouse setup makes step-sequencing an explicit artifact — use it. An irreversible destructive migration in the same release as the feature it serves should essentially never pass G3.

*SDK-facing contract changes* — **additive-only** rule: new optional fields yes; renamed/removed/retyped fields no, ever, without a versioned endpoint and a deprecation window measured in months. The SDKs live inside customer production apps; once a customer upgrades, *you* cannot roll their code back. And every new SDK capability ships with its own env-var kill-switch, following the `APILENS_CAPTURE_SPANS` precedent: env always wins, and can only turn the feature off.

**Gate G3 — what "approved" requires** (not an LGTM emoji):
- [ ] Blast-radius map re-confirmed against the actual design (bounce to G2 if it grew a tier)
- [ ] Rollback story written and plausible
- [ ] Migration sequencing explicit (expand/contract steps enumerated) if any schema changes
- [ ] Decommission plan exists for anything this replaces
- [ ] OPA policy addition identified for any new endpoint (fail-open means silence = allow)
- [ ] Tier 4 only: second reviewer signed, wire-format diff reviewed field-by-field

---

## 7. Phase 6 — Implementation Planning

**Why it exists.** The difference between a plan and a task list is *sequencing under partial failure*: at every point mid-build, production must be in a coherent state, because deploys can pause anywhere and priorities change mid-feature.

**Method — vertical slices, each independently shippable:**
1. Slice so each lands value or at least lands *safely dark* (deployed, unreachable, harmless).
2. Ship the schema expansion first, alone.
3. Ship backend logic dark or behind a flag.
4. Ship UI last, flag-gated.
5. **Schedule the decommission slice** for whatever this replaces — with a date, not "later." (See the dead-layer incident. "Later" means never.)

**Flag vs dark-ship:** dark-shipping (deployed but unreachable) suits backend plumbing; flags suit anything user-visible or needing percentage rollout. Flags are also debt — each flag gets a removal date at creation.

**Deliverable: sequencing doc** — table of slices with: what it contains, ship-mode (dark/flag/live), depends-on, "safe to stop after this?" (must be yes for every row), and estimated size. Owner: the engineer building it, reviewed by tech lead.

---

## 8. Phase 7 — Coding Workflow

**Why it exists.** Consistent mechanics make review attention go where machines can't: correctness, design, and blast-radius awareness — instead of formatting and typos.

**Conventions.**
- Branch per slice, PR per slice; small PRs (the dead-code cleanup this repo just did was reviewable *because* it was split into coherent commits).
- CI must gate merge on: lint, typecheck, full test suite, dependency/security audit. Humans should never spend review attention on anything a machine already checks.
- The current real-world gate — CI runs on fork PRs require a maintainer's manual approval — is a *feature* for Tier 3–4 changes (a human confirms the run should happen) and should be treated as a designed control point, not an annoyance to route around.

**AI-assisted coding, honestly placed.**
- **Good:** AI-drafted implementation; AI-generated test scaffolding; AI first-pass review *before* the human reviewer (catches the mechanical 60% so the human reviews the important 40%); AI-assisted "who else has this pattern" sweeps.
- **Never:** AI as the *sole* approver of anything Tier 4 (auth, billing, wire format), or as justification to skip post-deployment validation. The endpoint-table bug is precisely the class of defect that reads as perfectly plausible code to any reviewer, human or AI — it was *semantically* wrong about what data could exist in production, which no static reading catches.

**What the human reviewer owns:** does this match the approved design; does the blast-radius map still hold; is there a hidden Tier bump; are edge cases from the PRD actually handled; is the rollback lever really wired up. What CI owns: everything else.

---

## 9. Phase 8 — Testing Strategy

**Why it exists — and the honest starting point.** Testing depth must be *risk-based*, and this repo is candid proof that coverage is built incrementally: `apps/web` currently has zero test infrastructure; `apps/api` gained its first test files this cycle (on two branches, not yet unified); `packages/sdk-python` just received its first-ever suite; only `packages/sdk-typescript` is mature. The strategy below is designed for *that* reality — ratchet upward, don't pretend maturity.

**Test depth scales with tier, not with habit:**

| Tier | Required before merge |
|---|---|
| 1 — cosmetic | Typecheck + eyeball. Screenshot in PR. |
| 2 — internal logic | Unit tests for the changed logic; regression test if fixing a bug (test must *fail on the pre-fix code* — verify this, don't assume it). |
| 3 — customer-visible / schema | Tier 2 + integration test against real Postgres/ClickHouse + at least one E2E pass of the affected journey + edge-case checklist below. |
| 4 — wire format / auth | Tier 3 + **contract tests** (SDK payload golden-files validated against ingest schemas, in CI permanently) + explicit negative authz tests (OPA fail-open means you must *prove* denial, absence of an allow is not a test) + second engineer runs the E2E independently. |

**The edge-case checklist** (apply at Tier 3+; these are chosen because analytics products die on exactly these):
- [ ] Empty/sparse data (new project, zero traffic, one data point — most dashboards break here first)
- [ ] Malformed/oversized payloads at ingest
- [ ] Timezone & DST boundaries — this codebase has real timezone-bucketing logic in its ClickHouse analytics queries; a DST-transition day has a 23- and a 25-hour bucket once a year each
- [ ] Pagination boundaries (page beyond last, exactly page-size rows, page_size=0)
- [ ] Clock skew between customer SDK clocks and server time
- [ ] Concurrent writes / double-submit / retry-after-partial-failure

**Regression risk as an ongoing practice:** coverage ratchets (CI fails if coverage *drops*, no matter how low it currently is — this works even starting from near-zero); flaky tests get quarantined with an owner and a deadline, never silently skipped forever; every production bug's fix ships with the test that would have caught it.

**What testing cannot do — the setup for Gate G5.** The endpoint-table bug is the teaching case: a unit test with mocked data would have passed (the query logic was "correct" against the mock); only an integration test seeded through *the real live ingestion path* — or a human using the product — could reveal that the required Postgres rows could never exist. Some defects are wrong about *the world*, not about the code. That's why validation against production reality is its own gate and not a testing sub-task.

---

## 10. Phase 9 — Deployment Planning → Gate G4

**Why it exists.** Deployment is where abstract risk becomes concrete, and APILens's infrastructure makes the standard playbook partially inapplicable — so plan for the infra you have.

**The infra you have:** one Compute Engine VM running the entire docker-compose stack (Postgres, ClickHouse, Redis, OPA, api, ingest, web) behind Caddy. There is no fleet. Therefore:
- **"Canary" means in-process gating** — a feature flag enabled for N% of requests or a subset of projects — not infrastructure blue/green. Design the flag check into the code; the infra will not do it for you.
- **A bad deploy affects everything at once**, including the ingestion path customers depend on. This raises the value of dark-shipping and flags relative to a fleet-based shop, and it makes the single VM's resource headroom (CPU/RAM/disk) a first-class guardrail metric for any feature adding query or job load.

**Migration sequencing relative to code deploys** (expand/contract, operationalized): deploy N ships the additive migration + code reading both shapes; verify; backfill; deploy N+1 cuts over; deploy N+2 (days/weeks later) drops the old shape. Never combine "add new" and "remove old" in one deploy — that's what makes rollback a redeploy instead of a data-recovery incident.

**Gate G4 — pre-deployment go/no-go checklist** (deploy is blocked until all checked):
- [ ] All tier-required test evidence attached (Phase 8 table)
- [ ] Rollback runbook written and *rehearsed mentally step-by-step* (Phase 11) — including who flips what, in what order
- [ ] Kill-switch verified to actually work in staging (flip it, watch the feature die)
- [ ] Migration is expand-phase only; contract scheduled separately
- [ ] Monitoring for the *new code path specifically* exists before the deploy (you cannot validate what you cannot see)
- [ ] Guardrail baselines captured (current p95s, error rates, VM resource usage) — you need "before" to judge "after"
- [ ] Deploy window chosen with a human available for the validation window afterward

---

## 11. Phase 10 — Post-Deployment Validation → Gate G5

**Why this is a distinct gate.** Repeat of the core lesson because it earns the repetition: the endpoint-table bug passed review and would have passed most tests, and was caught only by running the product for real. "Deployed" and "working" are different claims; G5 is where the second one gets proven.

**The validation protocol (first 24–72h, scaled by tier):**
1. **Synthetic check:** exercise the new path yourself, end-to-end, immediately post-deploy — as a user, on production, with real (or realistically seeded) data. Not a curl to the healthcheck.
2. **Real-traffic watch:** monitor the new path *specifically* — its error rate, its latency, its output sanity (is the feature producing *plausible* results, not just 200s? An empty-but-200 response is precisely how the endpoint-table bug hid).
3. **Guardrail comparison:** current p95 / error rate / VM CPU-RAM vs. the pre-deploy baselines captured at G4.
4. **Dogfood — and this is a standing recommendation, not a one-off:** APILens is an API observability product; its own Django and FastAPI services should report into its own pipeline. Every deploy then validates the product twice — once as infrastructure, once as a product exercised against real traffic. This is also the cheapest permanent E2E test you will ever own.
5. **Intelligent monitoring:** static thresholds catch known failure modes; baseline-deviation detection ("this metric moved 3σ from its own trailing norm") catches the unknown ones. This capability is worth building for yourselves first — and it is simultaneously a customer-facing roadmap feature (see the worked example, §17).

**Gate G5 — decision thresholds (write real numbers per feature; these are sane defaults):**

| Signal | Promote | Hold & watch | Rollback |
|---|---|---|---|
| New-path error rate | < 0.5% | 0.5–2% | > 2%, or any auth/data-integrity error |
| Guardrail latency delta | < 5% | 5–15% | > 15% sustained |
| VM resource delta | < 10% | 10–25% | > 25% or trending toward exhaustion |
| Output sanity | Verified correct | Plausible, unverified | Implausible or empty-when-shouldn't-be |

"Hold" is a real outcome: keep the flag partial, keep watching, re-decide in 24h. The decision is made by the owning engineer + tech lead, and it is made *at a scheduled time* — not whenever someone remembers.

---

## 12. Phase 11 — Rollback Preparedness

**Why it exists.** The defining property of a rollback plan is that it was **authored before the deploy**. During an incident, cognition degrades and every minute is user-facing; the plan must already exist, be mechanical, and be executable by whoever is awake.

**The house kill-switch pattern — copy it.** `APILENS_CAPTURE_SPANS` establishes the template every new feature should follow:
1. An environment variable (or flag) that disables the feature entirely.
2. **Env always beats code-level config** — no code path can re-enable a feature ops turned off.
3. It can only turn the feature *off* — it never silently re-enables anything.
4. It is tested (this repo now has unit tests pinning exactly this behavior — falsey values, whitespace, precedence).

**Data reversibility rules:**
- Expand/contract makes code rollback safe *by construction*: the previous deploy still reads the old shape, which still exists.
- A destructive or irreversible migration in the same release as the feature it serves is close to never acceptable — it converts "flip a flag" into "restore from backup."
- If the feature *writes* new data (e.g. alert records), define upfront what happens to that data on rollback: orphaned-but-harmless (fine), or load-bearing (then rollback needs a data step — write it down now).

**Rollback readiness checklist (a G4 input — deploy is blocked without it):**
- [ ] Kill-switch exists, follows the env-wins/off-only pattern, and was flipped successfully in staging
- [ ] Previous-version redeploy path verified (image/tag still available, runbook step-by-step)
- [ ] No destructive migration rides with this release
- [ ] Rollback owner named for the validation window
- [ ] Post-rollback verification step written ("how we confirm the rollback itself worked")
- [ ] Data-on-rollback disposition decided and written down

---

## 13. Phase 12 — Continuous Improvement

**Why it exists.** Without a closing loop, the same class of failure recurs with different costumes. The three incidents cited throughout this document are valuable *only* because they were converted into rules (live-validation gate, "who else" audits, decommission slices). That conversion is this phase.

**The retro (within a week of G5, 30–45 min, all tiers ≥ 3):** produces not "went well / didn't" but **owned backlog items** — each with a person and a date — in three buckets: *fix the product* (defects and follow-ups), *fix the process* (which template/checklist/gate would have caught this earlier — then actually edit that template), *new opportunities* (feed directly into Phase 1 as opportunity briefs, closing the loop).

**A caution from this very repo:** the Playwright UX audit produced a genuine findings backlog — App Settings routes 404ing, a possibly-inverted Traffic filter, missing pages — and *nothing picked those items up*. A retro artifact nobody re-reads is a ritual, not a process. The fix is mechanical: retro items enter the same backlog as feature work and compete for the same prioritization at G1/G2, rather than living in a separate document that only entropy reads.

**Metrics of the process itself (review quarterly):** gate kill-rate (if G1/G2 approve everything, they're decoration), escaped-defect count per tier (are Tier assessments honest?), rollback frequency and mean-time-to-rollback (is the kill-switch discipline real?), flag debt (flags past their removal date).

---

## 14. Cross-cutting: Feasibility, Blast Radius, and Outcomes — applied continuously

**Feasibility is re-scored, not decided once.** Score at Phase 4 (schedule/don't), re-score at G3 (design may have revealed a tier bump — bounce to G2 if the answer changes), sanity-check at G4 (the world may have changed since design). A feasibility score older than the current gate is stale data.

**The blast-radius map is a living document.** It's drafted in Phase 4, re-confirmed at G3, and consulted at G4 ("did we build only what we mapped?"). Archived-after-approval maps are how the twenty-routes class of surprise happens — the map must be updated when implementation discovers a new dependency, and a *new row* on the map after G3 is a mandatory mini-review, not a shrug.

**Expected outcomes — the three-metric discipline.** Every enhancement defines, in the PRD, before build:
- **Leading indicators** (hours–days): adoption of the new path, its error rate, its output sanity. These drive G5.
- **Lagging indicators** (weeks): retention, ticket volume, revenue-adjacent movement. These drive the Phase-12 verdict on whether the feature *worked*, distinct from whether it *ran*.
- **Guardrails** (must not degrade): named metrics with numeric tolerances. **A met success metric plus a blown guardrail is a failed release** — you optimized a local number by taxing the whole product, and the framework treats it exactly like a defect.

---

## 15. Cross-cutting: The Refine / Rollback / Scrap Decision Tree

Applied at G5 and again when lagging indicators mature. Be mechanical about it — this decision is exactly where sunk-cost bias does the most damage.

```
Is a Tier-4 guardrail breached (auth/data-integrity/ingest availability)?
├── YES → ROLLBACK immediately. No debate. Diagnose from the safe state.
└── NO
    Is the CORE HYPOTHESIS invalidated?
    (users demonstrably don't want/use it — adoption near zero despite
     discoverability; or the signal it was built on turned out to be noise)
    ├── YES → SCRAP. Flip the kill-switch, schedule code removal as an explicit
    │         decommission slice (lesson of the dead layer: unshipped ≠ removed),
    │         write the graveyard entry, return to Phase 1 with the learnings.
    │         Do NOT "refine" a feature whose premise is dead — that is sunk cost
    │         wearing a process costume.
    └── NO (hypothesis holds; execution has problems)
        Estimate forward-fix cost vs. user pain while broken:
        ├── Fix ≤ 1 day AND guardrails only mildly degraded (hold-band, not
        │   rollback-band) → REFINE forward. Ship the fix through the normal
        │   (expedited) pipeline — it still gets G4/G5.
        ├── Fix > 1 day OR users actively hurting OR confidence in the diagnosis
        │   is low → ROLLBACK first, then refine calmly. Rolling back is not
        │   failure; it is the reversibility bias paying out.
        └── Repeated cycle? Two rollbacks of the same feature = automatic
            escalation to SCRAP-vs-REDESIGN review at G2 level. Three strikes
            means the design is wrong, not the luck.
```

Worked triggers with numbers: false-positive-heavy alerting feature where users disable it — adoption fell to 8% after trial, hypothesis ("users want automated alerts") *not* invalidated but execution (baseline too twitchy) at fault → **rollback to flag-off for affected users, refine the model, re-release through G4/G5**. Same feature but interviews reveal users actually wanted *weekly digests*, not real-time alerts → hypothesis invalidated → **scrap; new opportunity brief for digests.**

---

## 16. Cross-cutting deep dives

### 16.1 Edge cases & indirect impacts (applied at Phases 4, 8, and 10)

Systematic beats heroic. Three lenses, run as checklists:

- **Boundary analysis:** empty / one / max / negative / overflow, for every input and every dataset. For an analytics product: *the empty state is the most common state a new customer ever sees* — test it first, not last.
- **State-transition analysis:** what does the system look like mid-migration, mid-deploy, on retry-after-partial-failure, when the job scheduler fires twice? Every "then" in your sequencing doc is a state the system will actually occupy.
- **Indirect impact analysis:** the change you make can degrade something you never touched, through a shared resource. A new baseline-computation job adds ClickHouse load → the *dashboard*, which you didn't modify, gets slower. The twenty-routes incident is the structural cousin: twenty call sites shared a hidden dependency on one behavior none of them implemented. Ask, every time: *what shares a datastore, a connection pool, a CPU core (one VM!), or a copy-pasted pattern with the thing I'm changing?*

### 16.2 QA depth & regression risk — beyond the pyramid (Phases 7–10, ongoing)

- **Contract tests as a permanent CI gate:** golden SDK payloads validated against ingest's schemas on *every* CI run of either side — not a one-time integration check. The wire format is the product's spine; treat drift as a build failure.
- **Continuous synthetic canaries:** a scripted transaction (SDK sends → ingest stores → API serves → dashboard shows) running on a schedule against production. This is the automated, permanent version of the manual end-to-end run that caught the endpoint-table bug.
- **Mutation testing (or a poor-man's version — deliberately break the code, confirm tests fail):** especially valuable in a codebase where suites are new, to catch tests that pass without asserting anything real. The apps/api regression tests added this cycle were verified by running them against the pre-fix code and watching them fail — make that verification a habit, not an event.
- **Flaky-test policy:** quarantine with a named owner and a fix-by date. A silently-skipped test is worse than no test — it radiates false confidence.

### 16.3 Automation & AI-assisted workflows (honest placement, phase by phase)

| Phase | AI genuinely helps | AI must not |
|---|---|---|
| 1–2 Research/Discovery | Synthesizing tickets/interviews into themes; competitive-gap sweeps | Manufacture confidence — an AI summary of weak signal is still weak signal |
| 3 PRD | Drafting from the requirements doc; surfacing missing sections | Approve its own draft; G2 is human |
| 4–5 Impact/Design | Codebase-aware dependency mapping (`/graphify`); "who else has this pattern" sweeps; ADR drafting | Be the sole reviewer of a Tier-4 design |
| 7 Coding | Implementation drafts; first-pass review before the human | Sole approver on auth/billing/wire-format |
| 8 Testing | Test generation, edge-case brainstorming (then human-pruned) | Declare coverage "sufficient" |
| 10 Validation | Log triage; anomaly flagging against baselines | Authorize skipping G5, ever |
| 12 Retro | Pattern-mining across incidents | Own the action items |

The honest limit: AI review reads the code; the endpoint-table bug was wrong about *production reality*, which no reading of the code reveals. AI raises the floor of review quality; it does not replace the gate that checks the code against the world.

### 16.4 Observability & intelligent monitoring (Phases 9–12, and the roadmap)

- **Dogfood as policy:** APILens's Django/FastAPI services report into APILens itself. Every internal deploy becomes a product validation; every product gap felt internally is discovered before a customer feels it.
- **Baseline-deviation monitoring over static thresholds:** compute rolling baselines (e.g. trailing 7-day, hour-of-day-matched median + MAD) per service/endpoint; alert on sustained deviation (e.g. >3 MAD for 15+ minutes) rather than fixed numbers that go stale as traffic grows. Static thresholds catch failures you predicted; baselines catch the ones you didn't.
- **The meta-opportunity:** the exact capability above *is* a customer-facing feature for an observability product. Build it for yourself behind the standard lifecycle, validate it on your own traffic (the ultimate dogfood), then productize. Which is precisely the worked example below.

---

## 17. Worked Example: Idea to Production
### Feature: AI-assisted anomaly-detection alerts

*Endpoints get flagged when their error rate or latency deviates from their own rolling baseline — no static thresholds to configure — surfaced through the dashboard's existing Notifications nav item.*

**Phase 1 — Research.** Signals: two support requests asking "can I get alerted when something breaks?"; competitive check (Apitally/Datadog both ship static-threshold alerts; baseline-anomaly alerts are a differentiator at this price point); internal pain (we ourselves only noticed a prior real bug by manually looking at a dashboard). Opportunity brief scored: Reach 4 × Pain 4 × Fit 5 (alerting is the natural next organ of an observability product) × Confidence 0.8 = **64**. **G1: GO.**

**Phase 2 — Discovery.** Functional: per-project alert feed; anomaly = sustained deviation of error rate or p95 from that endpoint's own baseline; notification appears in the existing Notifications UI. NFRs with numbers: baseline job must add < 10% ClickHouse CPU; alert latency (anomaly onset → notification) < 10 min; **wire format: unaffected — SDKs and ingest untouched** (this single line keeps the whole feature out of Tier 4); authz: alerts scoped by the existing project-membership model, and the new endpoints need explicit OPA policies *because fail-open means forgetting one silently exposes other projects' alerts*. Out of scope: email/Slack delivery, user-configurable thresholds, per-consumer anomalies.

**Phase 3 — PRD → G2.** Goals: (1) users learn about incidents from APILens before their own users tell them; (2) zero-config alerting as a marketable differentiator. Non-goals: replacing PagerDuty; static threshold rules. Success metrics — leading: ≥ 30% of active projects view an alert within 14 days; alert-path error rate < 0.5%. Lagging: ≥ 1 support ticket citing an alert catching a real incident within 60 days. Guardrails: dashboard p95 within 5% of baseline; ClickHouse CPU +< 10%; VM RAM +< 15%; **false-positive rate — measured by alert-dismissal-without-click — under 40%.** Rollback sketch: `APILENS_ANOMALY_ALERTS` env kill-switch, off-only, env-wins. **G2: BUILD** — one blocking question ("compute on write or on schedule?") sent to a 2-day spike, which answered: scheduled job (write-path must never carry analytics cost — ingestion is the product's spine).

**Phase 4 — Impact & Feasibility.** Blast-radius map: ClickHouse — new baseline queries, *read* load only (Tier 3 driver); Postgres — new `AlertRule`/`AlertEvent` tables, additive (Tier 2); Django — new `/projects/{slug}/alerts` surface (Tier 2 + OPA policy); **new scheduled job — a genuinely new infra dependency on the single VM, flagged explicitly** (something must run cron-like where nothing did before; failure modes: silent non-execution, double-execution, resource contention with serving workloads); Next.js — settings page + Notifications integration (Tier 1–2); **ingest: unaffected; SDKs: unaffected; wire format: unaffected.** Overall: **Tier 3.** "Who else" audit via `/graphify`: the Notifications component's current data source, every consumer of the ClickHouse client (connection-pool sharing with dashboard queries). Feasibility 3.5 (from §5's worked scoring). **Decision: GO.**

**Phase 5 — Design → G3.** ADR-014: baselines = trailing 7-day hour-of-day-matched median + MAD per (project, endpoint), computed every 5 min by a scheduled job inside the api container (supervisor-managed loop; simplest thing that works on one VM — a separate scheduler container was considered and rejected as premature); anomaly = >3 MAD sustained for 3 consecutive windows (tunable constants, stored in code not DB, deliberately); alerts written to Postgres `AlertEvent`, deduplicated per (endpoint, kind, day). Alternatives recorded: ML model (rejected — unexplainable, heavier, and MAD is refinable later behind the same interface); ClickHouse materialized views (rejected for iteration speed on alert logic). Migration: purely additive Postgres tables — trivially expand-only. Decommission: nothing replaced. Rollback story: kill-switch stops the job and hides the UI; orphaned `AlertEvent` rows are harmless-by-design. **G3: APPROVED** with one condition — the job must emit a heartbeat metric so its silent death is detectable (accepted; wired into the dogfood pipeline).

**Phase 6 — Implementation plan.** Five slices, each safe-to-stop-after: (1) Postgres migrations, ship alone; (2) baseline job, **dark** — computes and logs, writes nothing user-visible, runs in prod for a week to observe real ClickHouse cost against the 10% guardrail *before* any user sees anything; (3) `AlertEvent` writes + Django API behind `APILENS_ANOMALY_ALERTS`, plus OPA policies; (4) Notifications UI integration, flag-gated; (5) settings toggle + docs. The week of dark slice-2 is the feature's cheapest and highest-value validation.

**Phase 7 — Coding.** One PR per slice. AI drafts the MAD/baseline math and its unit tests; human reviewer's checklist focuses on: timezone handling in hour-of-day matching (the known DST trap), ClickHouse query cost, and the env-wins kill-switch semantics. CI gates on lint/typecheck/tests; the maintainer-approval control applies to each PR's runs.

**Phase 8 — Testing (Tier 3 depth).** Unit: baseline math on synthetic series (flat, spiky, sparse, empty — a new endpoint with 2 data points must yield *no baseline*, not a division-by-near-zero hair-trigger; this is the empty-state lens). Integration: seeded ClickHouse → job run → correct `AlertEvent` rows in Postgres. Contract: none needed — wire format untouched, and *that* is verified by the existing SDK↔ingest contract suite staying green. E2E: seed an artificial error spike, watch the notification appear. Edge cases: DST-transition day buckets; alert dedup under job double-fire; pagination of a 1,000-alert feed. Negative authz test: member of project A requests project B's alerts → must be *denied* — proven, not assumed, because OPA is fail-open.

**Phase 9 — Deployment → G4.** Rollout: slices 1–2 live-but-dark (a week of real-cost observation); slices 3–5 behind the flag, enabled first for the team's own dogfood project only, then 25% of projects, then all. Migrations: additive-only, ride ahead of the code that uses them. G4 checklist walked: kill-switch flipped in staging and verified; previous image tag confirmed redeployable; baselines captured (dashboard p95, ClickHouse CPU, VM RAM); the job's heartbeat dashboard exists *before* the deploy; rollback owner named for the 72h window. **G4: DEPLOY.**

**Phase 10 — Validation → G5.** Synthetic: inject a spike into the dogfood project, alert arrives in 7 minutes — inside the 10-min NFR. Real-traffic watch at 25%: alert-path errors 0.1% (promote-band); ClickHouse CPU +6% (promote-band); dashboard p95 +2%; job heartbeat steady. Output sanity — the endpoint-table lesson applied: don't just check 200s, read the actual alerts generated for real projects and judge plausibility. Finding: plausible but *chatty* — early false-positive/dismissal rate ~35%, under the 40% guardrail but close. **G5: PROMOTE to 100%, with the false-positive metric flagged for daily watch** — a hold-adjacent promote, explicitly recorded.

**Phase 11 — Rollback readiness (was proven at G4, exercised never — but ready).** `APILENS_ANOMALY_ALERTS=false` stops the job and hides the UI within one restart; env-wins semantics unit-tested exactly like `APILENS_CAPTURE_SPANS`; orphaned alert rows harmless; no destructive migration exists to unwind.

**Phase 12 + the decision point — the realistic post-launch scenario.** Three weeks in, lagging metrics mature: dismissal-without-click has crept to **55%** — guardrail breached. Users are seeing alerts, shrugging, and dismissing; two have toggled the feature off. Walk the tree (§15): Tier-4 breach? No — nothing about auth/data/ingest is harmed. **Core hypothesis invalidated?** Check the evidence before assuming: adoption is *high* (users keep opening the alert feed), and interviews say "I want these, but half of them aren't real incidents." The hypothesis — users want zero-config anomaly alerts — *holds*; the execution — a too-twitchy 3-MAD/3-window model — is at fault. Forward-fix estimate: retuning windows + adding a minimum-traffic floor is ~2–3 days, and meanwhile users are annoyed but not harmed, and each user can already disable it individually. **Branch: REFINE — with a partial retreat**: flag dialed back to the 25% most-active projects (reducing annoyance surface while keeping signal), model retuned, re-released through G4/G5 with the false-positive guardrail tightened to 30%. The retro produces three owned items: *product* — the retune (owner, date); *process* — "guardrails measured only at G5 missed a metric that degrades over weeks; add a scheduled 30-day lagging-metrics review to Phase 12's template" (template edited that day); *opportunity* — two interviewees independently described wanting a weekly digest of anomalies rather than real-time pings → written up as a new opportunity brief and dropped into the Phase 1 queue, closing the loop.

Had the interviews instead revealed that users fundamentally didn't want automated alerts at all — adoption near zero, feed never opened — the same tree lands on **SCRAP**: kill-switch on, an explicit decommission slice scheduled (the dead-layer incident's lesson: turned-off is not removed), graveyard entry written, and the learning — not the code — carried back to Phase 1.

---

*Templates in this document (opportunity brief §2, discovery DoD §3, PRD §4, blast-radius map §5, ADR §6, tiered testing DoD §9, G4 checklist §10, G5 thresholds §11, rollback readiness §12) are meant to be copied into the repo and edited as Phase 12 learns things. A template that never changes is a template nobody is using.*
