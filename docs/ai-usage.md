# How AI tools were used

The brief asks for AI to be used intentionally "while maintaining correctness and quality", and
lists prompts and instructions as a committed artifact. This is an honest account, including the
things the AI got wrong.

## The shape of the work

The whole project was built with Claude Code, in four phases:

```
1. Contract first     requirements.md + api-contract.md, written before any code
2. Parallel build     two agents: one owning backend/, one owning frontend/
3. Adversarial review a third agent whose only job was to find problems
4. Fix and verify     each finding reproduced, fixed, and re-tested
```

**Why a contract first.** Two agents writing a client and a server simultaneously will invent
subtly different field names, enum spellings and error shapes, and the mismatch only appears at
integration when it is expensive. So `docs/api-contract.md` was written first and declared
binding: exact field names, exact enum values, the pagination envelope, the error envelope.
Neither agent was allowed to change it unilaterally.

That decision paid off. When the two halves were finally checked against each other — by parsing
the frontend's TypeScript interfaces and diffing every required field against live API responses
— **every object shape matched**. The only drift in the entire surface was one nullability
mistake (below).

**Why separate agents.** Backend and frontend touch disjoint files, so they can genuinely run in
parallel. Each was restricted to its own subtree and told to stage only its own paths
(`git add backend` / `git add frontend`), which kept their concurrent commits from colliding.

**Why an adversarial reviewer.** An agent that has just written code is a poor judge of it. The
review agent was given no stake in the implementation and explicit instructions to prove its
claims with runnable scripts, and to distinguish what it *proved* from what it *suspected*. That
framing is what produced the most valuable finding in the project.

## What the AI got wrong

This is the part worth reading.

**1. A confident, plausible, wrong root-cause analysis.** The backend agent measured
`GET /employees` at ~400–500ms and `by-dimension` at ~3s, and wrote in the README that the cause
was "the inherent width of the 8-way join evaluated per employee row on SQLite". That is a
credible-sounding explanation, and it was never tested against an alternative. Two alternatives
turned out to matter more:

- The checkout sits on a Windows drive mounted into WSL. A bare `SELECT COUNT(*)` costs 23ms
  there against 0.4ms on ext4. Copying the same database to a native filesystem and running the
  same binary took `by-dimension` from 2,980ms to ~80ms — **35x, with no code change**.
- Even after that, the query shape *was* wrong, just not for the stated reason.
  `EXPLAIN QUERY PLAN` ended in `USE TEMP B-TREE FOR ORDER BY` *after* every join: SQLite built
  all 10,000 joined rows, sorted them, then discarded all but 25. Fixing that took the default
  page from ~30ms to ~9.6ms and its count query from 26ms to 0.4ms.

So the first explanation was wrong, and the correction to it was itself only half right. Both
rounds are recorded in `docs/trade-offs.md` rather than quietly replaced.

**2. A concurrency bug that contradicted the project's own ADR.** ADR-002 claimed it was
"structurally impossible" to end up with two current salaries. The review agent disproved it with
a threaded script: two simultaneous raises each read the same open record, both close it, both
insert a new open row. The employee ends up with two current salaries, after which
`scalar_one_or_none()` raises and that employee can never be given a raise again without manual
database surgery. It is now enforced by a partial unique index, a row lock, and a 409 — and
ADR-002 records why the original claim was insufficient.

**3. A type that lied, defeating the type checker.** The frontend declared
`overall: PayEquityOverall` where the API returns `overall: null` whenever one side of a
comparison is empty. Because the *type* was wrong rather than its use, `tsc --noEmit` was clean
and the bug was invisible to tooling. It was latent — the dashboard renders that panel unfiltered
and the seed always has both genders — and would have crashed the first time anyone filtered it.

**4. A test that passed for the wrong reason.** After adding an `Employee.id` tie-breaker to
every sort, the accompanying test passed — and also passed with the tie-breaker removed, because
SQLite happened to return tied rows in a stable order anyway. The test docstring now says so
explicitly instead of implying it proves something it does not.

**5. Self-reported errors.** To its credit, the backend agent found and fixed a real pay-equity
bug on its own: the overall median was computed over a concatenation of per-group sorted lists,
which is not globally sorted, producing a nonsense gap over 100%. It reported this rather than
hiding it.

**6. A false alarm of my own.** The generated components imported `cn` from a bare `cn` package
rather than the usual local `clsx` + `tailwind-merge` helper, which looked exactly like a
hallucinated dependency. Checking before "fixing" showed it is real — `github.com/shadcn-ui/cn`,
shadcn's own compiled replacement. Verifying is cheaper than reverting.

## The discipline that caught these

- **Every fix was reverted to confirm the test fails without it.** Disabling the unique index
  fails three concurrency tests; removing the null guard reproduces
  `TypeError: Cannot read properties of null (reading 'gap_pct')`; restoring one per-row lookup
  fails the CSV query-count test 9 vs 29. A test that has never been seen to fail is not evidence.
- **Measure, don't reason, about performance.** Every latency number here came from running the
  thing, and two successive explanations were discarded because the measurement disagreed.
- **Verify claims against the code.** The reviewer was explicitly told to check whether the docs
  overclaim, which is how the ADR-002 problem surfaced.
- **Agents report what they could not verify.** The frontend agent stated plainly that it never
  saw a live backend and had not verified integration, rather than implying it had. That honesty
  is what prompted the separate integration pass that followed.

## The instructions given to the agents

Full prompts are long; the load-bearing parts were:

- *To both:* read `docs/requirements.md` and `docs/api-contract.md` first; the contract is
  binding — implement it exactly, do not rename fields or invent shapes. Own one subtree, stage
  only your own paths, commit incrementally with conventional-commit messages. Do not report
  success on unverified work.
- *To the backend agent:* no floats for money anywhere — integer minor units and `Decimal` with
  explicit rounding; salary is append-only and effective-dated, and the close-and-insert must be
  one transaction; analytics aggregate in SQL, never by pulling rows into Python; unit-test the
  compensation maths as pure functions with table-driven edge cases; actually run the server and
  curl every endpoint before reporting.
- *To the frontend agent:* money arrives as decimal strings, never `parseFloat` for anything but
  display; pagination, filtering and sorting are server-side — never fetch all 10,000 rows; keep
  filter state in the URL; one typed API layer, no `any`, no scattered `fetch`; `npm run build`
  is the hard gate. Do not block on the backend, and say plainly if you could not verify
  integration.
- *To the review agent:* you are reviewing, not rewriting — do not modify the repo. Prioritise
  correctness of the compensation domain, then test quality, then contract conformance. Where you
  suspect a bug, prove it with a runnable script, and distinguish what you proved from what you
  suspect. Do not soften findings, and do not invent problems to seem thorough.

## What AI was not used for

The decisions, not the typing: the data model (integer minor units, effective-dated salary
records, FX normalised in SQL), the scope boundaries and the reasoning for each exclusion, the
API contract, and the judgement calls on which review findings to act on and which to accept
and document. The 12ms cost of the pagination tie-breaker, for instance, is a deliberate
trade — correctness over speed on a non-default sort — not something an agent decided.

## Honest limits of what was verified

- `docker compose up` has **never been executed** — Docker is not available in this environment.
  The Dockerfiles and compose file are written and reviewed but unproven.
- No browser click-through. Integration was verified by diffing live API responses against the
  frontend's TypeScript types, confirming CORS preflight for the UI origin, confirming Windows
  can reach the WSL-hosted API, and confirming all three pages render — but nobody has actually
  clicked "Record a raise" in a browser.
- The Postgres code paths (`percentile_cont`, `width_bucket`) are exercised only by the SQLite
  fallback's mirrored tests. A CI job against a real Postgres service is the obvious next step.
