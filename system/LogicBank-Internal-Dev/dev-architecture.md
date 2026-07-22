---
title: Developer Architecture for LogicBank
Description: Enables AI assistants to be co-designers for LogicBank development
Usage: AI assistants read this to understand project structure, development workflow, testing, and release process
version: 1.16
changelog:
  - 1.16 (Jul 2026) - New passive-delete-cascade-typo.md: fixed GitHub issue #22 (LogicRow._cascade_delete_children() passed a nonexistent do_not_adjust=self keyword to LogicRow.delete(), which only accepts do_not_adjust_list - TypeError on every delete of a parent whose child relationship declares cascade="all, delete" + passive_deletes=True). One-line fix (do_not_adjust_list=[self]), matching the sibling client-delete call site in listeners.py. Zero prior test coverage of this combination anywhere in the repo. New regression suite examples/passive_delete_cascade/.
  - 1.15 (Jul 2026) - New spurious-parent-dependency.md: fixed GitHub issue #21 (parse_dependencies registered any 3+-node row.X.Y token as a parent dependency without checking X was a real relationship - a chained method call on a plain column, or a paren-stripping artifact from a sub-query, crashed on update or killed activation of the entire rule set). Fixed via AbstractRule._is_relationship_node(). Also ratified the `# deps:` comment convention for calling= formulas (documented in Rule.formula's docstring and dependency-scanning.md, not a code change). New regression suite examples/spurious_parent_dependency/.
  - 1.14 (Jul 2026) - commit-event-mutation-gap.md updated to v2.0: implemented the fix (activate()-time LBActivateException if a RowEvent/CommitRowEvent's calling= source appears to write row.<attr> =, with allow_row_mutation=True escape hatch); scope corrected to cover RowEvent (not just CommitRowEvent - same bug, fires after the same cascade); AfterFlushRowEvent confirmed to have a different, lesser footgun (mutation silently dropped by SQLAlchemy, not persisted) and left out of scope. New regression suite examples/commit_event_mutation_scan/.
  - 1.13 (Jul 2026) - Documentation Map was missing dependency-scanning.md and after-flush-row-event-conditions-bug.md (both already existed, just never indexed here) - added, plus new commit-event-mutation-gap.md (open, not fixed: CommitRowEvent mutations bypass derivation/constraint checking, confirmed empirically while designing CommitConstraint).
  - 1.12 (Jun 2026) - Added forward-looking flag: Val is considering retiring WebGenAI (replaced by a simplified VS Code-like shell), now that Claude rarely produces the malformed-rule failures WebGenAI's web-UI-as-error-surface design existed to handle. Flagged as a reason to re-check whether LBActivateException's structured-error contract is still load-bearing, if/when that happens - not acted on, just don't assume the constraint is permanent.
  - 1.11 (Jun 2026) - Added dragons-deferred-adjustment.md reference: a separate, already-fixed killer bug (nondeterministic session.dirty order causing wrong-parent aggregate adjustment, ~50% reproduction rate). Promoted from $readme.txt scratch notes (deleted) to a proper doc; verified the bug_explore reproduction hook in listeners.py still exists but is bit-rotted (get_old_row() signature mismatch) - documented as broken, not working, after testing it directly.
  - 1.10 (Jun 2026) - readme_dev.md split: testing content moved to run_tests_readme.md (repo root, stays human-discoverable), release-management content moved to system/LogicBank-Internal-Dev/release-management.md (new file). Updated all cross-references in this file, CLAUDE.md, and basic_demo_sample.md accordingly. Added CLAUDE.md at repo root as the bootstrap entry point.
  - 1.9 (Jun 2026) - multi-relationship-bug.md now covers full blast radius: Rule.copy (no role param, raises TODO on ambiguity) and parent-refs/insert-link (open thread) added alongside Sum/Count
  - 1.8 (Jun 2026) - CONFIRMED multi-relationship-bug.md against github.com/valhuber/LogicBank/issues/20 - root cause matched exactly; issue narrows fix to Sum only (Count already has correct precedence: explicit child_role_name wins before falling back to get_child_role_name())
  - 1.7 (Jun 2026) - Added multi-relationship-bug.md reference: root-caused the suspected GenAI-Logic bug to a fallthrough/wrong-attribute defect in aggregate.py get_child_role_name() that defeats the child_role_name disambiguator for multi-relationship-to-same-parent cases
  - 1.6 (Jun 2026) - Added Design Lineage section: Versata virtual-vs-stored aggregate distinction, Kolk Oil + State of Utah production performance incidents (minutes vs seconds, caused by virtual aggregates at volume), and why LB closes off this failure class by having no virtual mode (adjustment always on)
  - 1.5 (Jun 2026) - Added Executable (Governed) Requirements section: scope of the capability, CLVS (Gherkin/EAI/Kafka) and Customs Surtax (regulation-text-driven, governance_report scoring) as flagship proof points, why both are high-scrutiny consumers of LB rule-firing/snapshot semantics
  - 1.4 (Jun 2026) - Read build_and_test/genai-logic/README.md: added "no second door" before_flush enforcement quote, and noted a 3rd/4th Northwind-shaped artifact (samples/nw_sample(_nocust), samples/basic_demo_logic_gov A/B procedural-vs-declarative comparison) distinct from LB examples/nw and BLT tests/ApiLogicProject
  - 1.3 (Jun 2026) - Documented release coupling (LB tests/releases first, GL pins exact version after) and prototypes/base CE (.copilot-instructions.md + docs/training/logic_bank_api.md "Rosetta Stone" + logic_bank_patterns.md) - notably the documented FK/relationship-resolution constraints (never derive FK via Rule.formula/copy; attach children via parent.ChildList.append not raw FK) relevant to suspected LB/GL relationship-modeling bug
  - 1.2 (Jun 2026) - Added Testing: Two Layers section (LB run_tests.py vs GenAI-Logic BLT; nw+/allocation fixtures are separate, similar-not-identical; pointer to GL's own dev-architecture.md for Gold source / BLT mechanics)
  - 1.1 (Jun 2026) - Added basic_demo_sample.md reference (model + LB activation in a real GenAI-Logic project)
  - 1.0 (Jun 2026) - Initial CE for LogicBank: links readme_dev.md, references wiki Logic-Walkthrough
---

# Context Restoration: LogicBank Development

**Purpose:** This file (and sibling files in this folder) establish AI assistant context for working on the LogicBank repo itself — the standalone rules engine consumed by [ApiLogicServer / GenAI-Logic](https://github.com/valhuber/ApiLogicServer).

**See also [run_tests_readme.md](../../run_tests_readme.md)** (repo root) — the human-facing testing guide: how to run tests and debug failures. And **[release-management.md](release-management.md)** (this folder) — version bump, build, and PyPI release process (split out of the old `readme_dev.md`). This file and its siblings are AI-context-first (architecture, lineage, bug investigations); `run_tests_readme.md` stays at repo root since it's the conventional, human-discoverable "how do I test this" doc. They're complementary, not duplicates — this file points *to* them rather than restating their content (see "Testing: Two Layers" below).

&nbsp;

## 🎯 What LogicBank Is

LogicBank is a declarative, transactional business-logic engine for SQLAlchemy. Rules (`Rule.constraint()`, `Rule.sum()`, `Rule.formula()`, `Rule.copy()`, etc.) are declared against mapped classes; LogicBank hooks SQLAlchemy's `before_flush` event and executes them via forward-chaining when a commit occurs.

**Consumed by:** ApiLogicServer / GenAI-Logic embeds LogicBank as its rules engine. Changes here propagate to every ApiLogicServer-created project (via the `prototypes/base` template's `logic/` folder and the Rosetta Stone CE in `.copilot-instructions.md`).

**GL's own one-sentence description of the enforcement guarantee** (from `build_and_test/genai-logic/README.md`), worth keeping verbatim since it's the precise technical claim underneath all the "can't be bypassed" marketing language: *"rules aren't called from your code — they're wired into a single SQLAlchemy `before_flush` listener, installed once at server start. Every write, from any path — API, custom endpoint, Kafka consumer, agent — passes through that one listener before it commits. There's no second door."* This is the architectural fact to verify/preserve when touching activation (`LogicBank.activate()`) — GL's entire governance pitch rests on there being exactly one listener, registered once.

&nbsp;

## 📚 Documentation Map

This repo has no `docs/` source tree — documentation lives in two places:

1. **[GitHub Wiki](https://github.com/valhuber/LogicBank/wiki)** — the gold source for conceptual/architecture docs. It's its own git repo (`git clone https://github.com/valhuber/LogicBank.wiki.git`), not generated from anything in this repo.
   - **[Logic-Walkthrough](https://github.com/valhuber/LogicBank/wiki/Logic-Walkthrough)** — the internals deep-dive: how `RuleBank`, `LogicRow`, forward chaining, cascade, and aggregate-adjustment pruning actually work. Read this before modifying `logic_bank/exec_row_logic` or `logic_bank/exec_trans_logic`. Summary:
     - Rules are declared as extensions to SQLAlchemy models; engine only acts at commit time (not on raw SQL / bulk updates)
     - `LogicBank.activate()` registers `before_flush` listeners, loads rules via a declarator function, detects dependency cycles
     - Each modified row becomes a `LogicRow`; ordered phases: copy → formula → aggregate adjust → constraint → child cascade
     - Forward chaining propagates across tables (e.g. OrderDetail.Quantity → Amount → Order.AmountTotal → Customer.Balance)
     - `ParentRoleAdjustor` coalesces multiple sum/count changes into exactly one parent update per role
     - Formula execution is pruned when referenced attributes haven't changed
     - Cascade tags *which* parent role changed, so children selectively recompute only affected formulas
2. **[run_tests_readme.md](../../run_tests_readme.md)** (this repo, root) — practical testing guide: test running (`run_tests.py`, VS Code launch configs), why pytest/Test Explorer don't work here.
3. **[release-management.md](release-management.md)** (this folder) — the full release process (version bump in `logic_bank/rule_bank/rule_bank_setup.py`, `pyproject.toml` build, twine upload).
4. **README.md** (this repo, root) — public-facing overview/intro.
5. **[basic_demo_sample.md](basic_demo_sample.md)** — how GenAI-Logic's `manager/samples/basic_demo_sample` defines data models and wires up/activates LogicBank in a real generated project (the canonical "5 rules replace 200 lines" check-credit example, in its actual shipped form).
6. **[multi-relationship-bug.md](multi-relationship-bug.md)** — investigation, fix, and 21-test regression suite for the multi-relationship-to-same-parent-class bug family ([GitHub issue #20](https://github.com/valhuber/LogicBank/issues/20) and related): `Rule.sum`, `Rule.count`, `Rule.copy`, `Rule.formula` live-cascade, `LogicRow.link()`, and a null-optional-FK adjustor crash found along the way — all fixed and tested.
7. **[dragons-deferred-adjustment.md](dragons-deferred-adjustment.md)** — a different, older, *already-fixed* killer bug: nondeterministic `session.dirty` iteration order could cause an aggregate adjustment to land on the wrong (or both, or neither) parent when a transaction reparents a child AND changes a sum-contributing attribute in the same commit. Silent wrong-answer, ~50% reproduction rate. Read before touching `LogicRow.save_altered_parents()` or `listeners.py`'s row-iteration logic.
8. **[dependency-scanning.md](dependency-scanning.md)** — how `Formula`/`Constraint` dependency scanning works across `as_exp`/`as_expression`/`calling=`: `calling=` functions ARE scanned via `inspect.getsource`, but the scan is textual/`row.`-prefix-only — `old_row.` references are invisible, and calls into helper functions aren't followed.
9. **[after-flush-row-event-conditions-bug.md](after-flush-row-event-conditions-bug.md)** — `AfterFlushRowEvent.if_condition`/`when_condition` were never evaluated, a stack of masking bugs in `row_event.py`; already fixed, plus a separate cross-commit nesting-guard leak in `listeners.py`'s `after_flush` that silently killed *all* row-event types on a session-resident row after its first commit (also fixed).
10. **[commit-event-mutation-gap.md](commit-event-mutation-gap.md)** — `row.attr = value` inside a `Rule.row_event`/`Rule.commit_row_event` handler used to be silently persisted without ever re-triggering `Formula`/`Sum`/`Count`/`Constraint`/`CommitConstraint` for that row, since both fire after that row's rule cascade has already completed for the flush, with no second pass. Confirmed empirically; **now fixed** — `activate()` fails fast (`LBActivateException`) if a textual scan detects the write, with `allow_row_mutation=True` as an opt-out. `AfterFlushRowEvent` has a different, lesser version of this (mutation silently dropped by SQLAlchemy, not persisted) and is out of scope for the guard.
11. **[spurious-parent-dependency.md](spurious-parent-dependency.md)** — [GitHub issue #21](https://github.com/valhuber/LogicBank/issues/21): `parse_dependencies` used to register any 3+-node `row.X.Y` token as a parent dependency without checking `X` was a real relationship — a chained method call on a plain column (`row.code.zfill(8)`) crashed every subsequent update, and a paren-stripping artifact from a sub-query (`row.id_customer).scalar()`) killed activation of the *entire* rule set. "The unfinished half of #14" — that fix counted nodes but never validated the middle one. **Fixed** via `AbstractRule._is_relationship_node()`. Also ratifies the `# deps:` comment convention (see [dependency-scanning.md](dependency-scanning.md)) for `calling=` formulas whose parent access is hidden inside a helper function.
12. **[passive-delete-cascade-typo.md](passive-delete-cascade-typo.md)** — [GitHub issue #22](https://github.com/valhuber/LogicBank/issues/22): `LogicRow._cascade_delete_children()` called `.delete(do_not_adjust=self)` — a keyword `LogicRow.delete()` doesn't accept (it's `do_not_adjust_list`, a list). `TypeError` on every delete of a parent whose child relationship declares both `cascade="all, delete"` and `passive_deletes=True` (the only combination that routes through this method rather than the normal client-delete path). **Fixed**: one-line correction (`do_not_adjust_list=[self]`), matching the sibling call site in `listeners.py`. Zero prior test coverage of this combination anywhere in the repo, which is why it shipped unnoticed.

&nbsp;

## 🧭 Quick Reference

| Need | Where |
|---|---|
| How rules execute internally | [Logic-Walkthrough wiki](https://github.com/valhuber/LogicBank/wiki/Logic-Walkthrough) |
| Run/debug tests | `run_tests_readme.md` (repo root) |
| Cut a release | `release-management.md` (this folder) |
| Version source | `logic_bank/rule_bank/rule_bank_setup.py` (`__version__`) |
| Example projects (test fixtures) | `examples/<name>/tests` (banking, nw, copy_children, payment_allocation, referential_integrity, custom_exceptions, insert_parent, tutorial) |
| Core engine code | `logic_bank/exec_row_logic/`, `logic_bank/exec_trans_logic/`, `logic_bank/rule_bank/` |

&nbsp;

## 🧪 Testing: Two Layers

LogicBank changes are tested in **two separate passes**, against **two separate (but related) test fixtures**:

### 1. LogicBank repo tests (this repo) — engine-level, fast, in-process

Run via `python3 run_tests.py` (see `run_tests_readme.md`, repo root). Tests instantiate SQLAlchemy sessions directly and call `LogicBank.activate()` in-process — no HTTP, no Flask, no web server. Fixtures: `examples/nw` (the bigger one — Northwind, 16+ tables, exercises relationship edge cases) and `examples/payment_allocation` (the LB-side allocation example), plus banking, copy_children, referential_integrity, custom_exceptions, insert_parent, tutorial.

### 2. GenAI-Logic BLT (Build-Load-Test) — integration-level, slower, full-stack

Run from the **Seminal Manager** (`ApiLogicServer-dev/org_git/ApiLogicServer-src/tests/build_and_test/build_load_and_test.py`). This is GenAI-Logic's own smoke-test suite — it creates ~18 real generated projects (API + Admin UI + DB), starts each as a live server, and validates over real HTTP. It is **not** LogicBank-specific, but it includes the two fixtures most relevant to LogicBank changes:

- **Northwind** — `Config.do_create_api_logic_project` creates `tests/ApiLogicProject` via `ApiLogicServer create --db_url=nw+` (the `+` suffix means "with logic" — see `fix_database_models()` / `fix_nw_datamodel()` in `api_logic_server_cli/api_logic_server.py`). `validate_nw()` then runs **behave tests + live REST calls** (e.g. `GET /filters_cats`, `POST .../get_cats`) against the running server — testing the same check-credit/order logic as LB's `examples/nw`, but end-to-end through the generated API/Admin UI, not via direct SQLAlchemy session calls.
- **Allocation** — `Config.do_allocation_test` creates `tests/Allocation` via `ApiLogicServer create --db_url=allocation` (builtin fixture: `api_logic_server_cli/database/allocation.sqlite`), starts the server, then runs `sh test.sh` from the project's `test/` folder. Conceptually the same scenario as LB's `examples/payment_allocation`, but it's a **separate, independently-maintained database/project**, not a copy or export of the LB fixture — schemas and test scripts can and do drift apart.

**Update — a third and fourth Northwind-shaped artifact exist too** (per `build_and_test/genai-logic/README.md`, the Manager's own welcome doc): the Manager's `samples/` folder ships **pre-built, human-facing demo projects**, separate again from both LB's `examples/nw` and BLT's `tests/ApiLogicProject`:
- `samples/nw_sample_nocust` — plain Northwind, `ApiLogicServer create --db-url=nw` (no customizations) — "reflects the results you can expect with your own databases"
- `samples/nw_sample` — same DB, **with hand-added customizations** (`ApiLogicServer create --db-url=nw+`) — search `#als` to find them; a customization reference, not a test fixture
- `samples/basic_demo_logic_gov` — yet another basic_demo variant, notable for containing **both** `logic/procedural/credit_service.py` (hand/AI-written procedural code) and `logic/logic_discovery/place_order/check_credit.py` (the 5-rule declarative version) side by side — this is the literal A/B comparison artifact the CE/marketing "44X reduction" claim is measured from

So: **four** Northwind-shaped things exist across the two repos (LB `examples/nw`, BLT `tests/ApiLogicProject` via `nw+`, Manager `samples/nw_sample(_nocust)`), each serving a different purpose (engine unit tests / integration smoke test / human demo+customization reference) and each independently maintained. Don't assume a fix verified in one is verified in another.

**Key implication:** "similar, not identical." Both NW and Allocation exist in both places because they're useful test scenarios for both projects — but they are **independently maintained fixtures**, not the same files. A bug fixed/reproduced against LB's `examples/nw` is not automatically validated against BLT's `nw+` Northwind (and vice versa) unless you explicitly run both passes. **Workflow: test in LogicBank first (`run_tests.py`), then re-test in GenAI-Logic via BLT** before considering a LogicBank change complete — BLT is the integration check that catches consumer-side breakage (generated-model shapes, API-level behavior) that the LB-only suite can't see.

**Where to look things up:** GenAI-Logic's own `dev-architecture.md` (`build_and_test/genai-logic/system/ApiLogicServer-Internal-Dev/dev-architecture.md`) explains the **Gold source** convention and BLT mechanics in detail — read it (or its "Documentation Navigation Map" / "Development Workflow" sections) before assuming a path; BLT regenerates the local workspace on each run, so file locations under `build_and_test/ApiLogicServer/` are transient, while the actual source of truth lives under `org_git/ApiLogicServer-src/`. In particular:
- BLT script (gold source): `org_git/ApiLogicServer-src/tests/build_and_test/build_load_and_test.py`
- Per-developer config (which tests run): `org_git/ApiLogicServer-src/tests/build_and_test/env_val.py` (and sibling `env_*.py` files)
- Northwind/Allocation project folders only exist **after** a BLT run, under `build_and_test/ApiLogicServer/tests/ApiLogicProject` and `.../tests/Allocation` respectively — don't expect to find them pre-existing on disk

&nbsp;

## ⚡ Design Lineage: Why Aggregate Adjustment Is Always On

**Background (from Val):** LogicBank's algorithms are different from Versata's, but the concepts carry forward — both are roughly the same order of architectural complexity as a query optimizer (dependency graph, ordering, pruning, all on declarative input rather than procedural).

**The Versata virtual/stored distinction:** at Versata, a `Sum`/`Count` attribute could be defined **virtual** (computed on read via a live `SELECT SUM(...)`, no stored column) or **stored** (a real column, maintained incrementally on every write by the adjustor — exactly one update per parent per role, no matter how many children changed in the transaction). Switching virtual → stored is what "activated the adjustment logic."

**Two real-world incidents this caused, both the same shape — fine in dev, broke in production at volume:**
- **Kolk Oil** — an Allocation System built on Versata. Ran fine through dev. At live-volume test, performance went from the 1-2 sec SLA to 3-4 minutes. Root cause: the relevant aggregate was defined virtual — fine against small dev datasets where a live re-aggregate is cheap, catastrophic at production volume where the same aggregate gets recomputed on every dependent read. Fix: switch the attribute to stored, activating the adjustor (O(1) delta-update per write instead of O(n) recompute per read).
- **State of Utah unemployment system** — a similar minutes-vs-seconds regression, same underlying cause (virtual aggregate recomputation at volume the dev environment never exercised).

**Why this matters for LogicBank today:** LB has **no virtual/stored distinction** — `Rule.sum`/`Rule.count` always materialize into a real, physically-updated column (this is also *why* GL's GenAI prompt engineering insists "if you create sum/count/formula rules, you must create a corresponding column in the data model" — there's no virtual escape hatch to fall back to). The `ParentRoleAdjustor` mechanism (Logic-Walkthrough wiki: "ensures exactly one parent update per role for multiple aggregates... collecting changes from all sums/counts before persisting a single parent update") is **unconditionally active** — there's no mode to accidentally leave in the slow, virtual-equivalent state. This closes off the entire failure class that bit both Kolk Oil and Utah: there's no dev-vs-prod cliff hiding behind a "virtual" setting nobody remembered to flip, because that setting doesn't exist. Worth treating as one of LogicBank's quiet, deliberate simplifications over the Versata design — not just a missing feature.

&nbsp;

## 🏛️ Executable (Governed) Requirements — Top of the Stack

LogicBank is the substrate under GL's highest-level capability pitch: **Executable Requirements**. Worth understanding the scope, since it's the context in which "is LogicBank's enforcement trustworthy" gets tested hardest.

- **Executable** — `docs/requirements/<name>/requirements.md` is not a handoff doc an AI "interprets" once; it's read and directly executed (`implement reqs <name>` in Copilot Agent mode), building the system, then writing `ad-libs.md` back alongside it — an audit trail of every assumption/decision, flagged 🔴 (needs PM/dev review) vs 🟡 (FYI, standard pattern). Designed as a repeatable loop: tighten the spec, rerun, narrow the AI's decision space each cycle. General mechanism documented in `samples/requirements/readme_reqmts.md`; demoed end-to-end via `demo_eai`.
- **Governed** — the resulting system inherits LogicBank's enforcement guarantee (the "no second door" `before_flush` listener, above) — so the requirement becomes *enforced policy*, not documentation that can drift from the build. Enforcement is itself auditable via the governance/health-check reports (coverage score = weighted rules/table, integrity score = demerits for anti-patterns, red-flag check for un-adopted aggregation rules).

**Two flagship proof points, deliberately different in kind** (`samples/demo_customs_clvs`, `samples/demo_customs_surtax`):

- **CLVS** (`docs/requirements/customs_demo/requirements.md`) — a **Gherkin-scenario** spec with deep EAI integration: subscribe to Kafka (`isdc` topic, CIMCorp shipment XML), parse/persist with field mappings, duplicate-replay policy (`fail|replace`, matched by business key), PK-collision normalization (placeholder `0` IDs → `None` so autoincrement assigns real PKs), then a CLVS-eligibility constraint rule (value threshold, prohibited-commodity check, tariff lookup). Proves the pattern handles **integration-heavy, message-driven** requirements where data-correctness subtleties (replay idempotency, placeholder-ID collisions) matter as much as the business rule itself.
- **Customs Surtax** (`docs/requirements/cbsa_steel_surtax/requirements.md`) — built directly from **actual government regulation text** (CBSA Steel Derivative Goods Surtax Order, PC Number 2025-0917, citing specific Customs Tariff subsections/paragraphs). 5 tables, 17 rule declarations (3 sum, 6 formula, 7 copy, 1 constraint). Its `governance_report.md` is a worked example of the audit angle: scores Coverage 7.2 / Integrity 94, and — notably — flags that the AI's `declare_logic()` docstring **paraphrased the regulation into an invented eligibility list instead of quoting it verbatim**, which the governance tooling treats as a real finding (docstring-hygiene demerit), not a style nit. Proves the pattern works for **compliance-grade** requirements where fidelity to source legal text is part of correctness, not just the logic.

**Why this matters for LogicBank work:** these two samples are the highest-scrutiny consumers of LB's rule semantics in the whole GL system — Kafka-driven inserts racing against LB's dependency/cascade timing (CLVS), and `Rule.copy` snapshot-vs-live semantics carrying real regulatory weight (Surtax's `country_surtax_rate` is deliberately snapshotted at entry time, not live, "so a rate correction next month doesn't silently re-price last month's filings" — a regulatory argument for `Rule.copy` over `Rule.formula`, not just a style choice). Any LB engine change should be sanity-checked against what these two requirements docs assume about rule firing order and snapshot timing.

&nbsp;

## 🚩 Forward-looking flag: WebGenAI may be retired — watch for downstream LB scaffolding becoming dead weight

**Val's stated direction (Jun 2026), not yet decided/acted on:** WebGenAI ("WebGenie") was built to solve a specific problem — early OpenAI-generated rules routinely failed (malformed/missing attributes), and WebGenAI's web UI had no IDE and no developer in the loop, so it had to *be* the error-surfacing and recovery mechanism itself (see the `LBActivateException.invalid_rules`/`.missing_attributes` background in `basic_demo_sample.md` → "Why this matters for LogicBank Engine Changes"). Val's instinct: now that Claude rarely fails at this kind of generation, that whole problem may be largely solved at a different layer — replace WebGenAI with something closer to a simplified VS Code shell ("hides the sharp knives") rather than maintaining a bespoke web UI + fixup pipeline built around an AI failure mode that's becoming rare.

**Why this is flagged here, not just a GL-side note:** if WebGenAI retires, the GenAI-pipeline-specific scaffolding *inside LogicBank* that exists solely to serve it — the structured `LBActivateException` fields, anything else found to be fixup-loop-specific — becomes a second-order cleanup candidate. Not urgent, not decided, but worth re-checking this assumption (`LBActivateException`'s structured-error contract being load-bearing for a live consumer) if WebGenAI's retirement actually happens — what's "a consumed public API, don't break it" today may become "dead code, safe to simplify" later. Don't act on this preemptively; just don't assume the constraint is permanent when revisiting that exception's design.

&nbsp;

## 🔄 Relationship to ApiLogicServer Dev Workspace

LogicBank is developed, tested, and versioned **independently in this repo first**. The release loop is:

1. Bump version in `logic_bank/rule_bank/rule_bank_setup.py`, run `python3 run_tests.py` here until green
2. Build + release to PyPI (see `release-management.md`)
3. Bump the pinned LogicBank version in GenAI-Logic's `pyproject.toml`/`requirements.txt`
4. Re-run BLT in GenAI-Logic to validate the new version against the integration fixtures (see Testing: Two Layers, above)

GL does **not** float to latest LB — it pins an exact version, bumped deliberately after LB's own tests pass. So a LB fix isn't "live" for GL until steps 3-4 happen.

### How GenAI-Logic projects actually consume LogicBank: `prototypes/base`

Every project `genai-logic create` (or `ApiLogicServer create`) produces is cloned from **`api_logic_server_cli/prototypes/base`** — the template GL overlays onto a freshly-introspected (or GenAI-generated) data model. This is the "Method 4 / SCS" path referenced in the Manager workspace instructions. `prototypes/base` is also where the CE that teaches AI assistants the LogicBank rule API actually lives — it gets copied into every created project's `.github/` and `docs/training/`, so it's worth knowing what's in it when debugging consumer-side LB usage:

- **`prototypes/base/.github/.copilot-instructions.md`** (~2200 lines, grown from the ~740 noted in GL's own dev-architecture.md) — the per-project CE entry point. Section **"Adding Business Logic"** has a mandatory pre-flight read list before an AI may write any rule:
  1. `docs/training/logic_bank_patterns.md` (foundation)
  2. `docs/training/logic_bank_api.md` (the rule API itself — "Read Second")
  3. `docs/training/allocate.md` (Allocate pattern — distribute/split amounts to children)
  4. `docs/training/probabilistic_logic.md` (AI-callable rules)
  5. `docs/training/RequestObjectPattern.md` (integration services)
  6. `docs/training/eai_subscribe.md` (Kafka EAI consume)

  Also contains a documented, hard rule for child-row insertion relevant to relationship modeling:
  > ✅ REQUIRED: `parent.ChildList.append(child_row)` or equivalent relationship attach
  > ❌ FORBIDDEN: `session.add(child_row)` with only raw FK columns set
  > REAL FAILURE CASE: standalone child insert can trigger "Missing Parent" during flush even though the FK value looks correct.

  This is a GL-side convention layered on top of LogicBank — LB itself doesn't enforce attach-via-relationship, but GL's CE does, because of an observed failure mode. **Worth checking against any reported bug involving child-row creation.**

- **`prototypes/base/docs/training/logic_bank_api.md`** (932 lines, versioned independently — currently "1.0.16") — **the actual "Rosetta Stone."** This is GL's canonical LogicBank rule-syntax reference, the thing AI assistants are required to read before writing any `Rule.*` call in a project. Key content relevant to LB-engine work:
  - **Core principle:** "path-independent rules = automatic reuse" — one rule covers insert/update/delete/parent-change, no use-case explosion
  - **Directory/discovery convention:** prompt phrasing → `logic/logic_discovery/<use_case>/<file>.py` (requirements traceability)
  - **CRITICAL — never derive a foreign key column with `Rule.formula`/`Rule.copy`:** "FK columns drive SQLAlchemy relationship resolution. If LogicBank re-derives an FK mid-transaction it conflicts with how SQLAlchemy manages object identity and relationship loading, producing unpredictable behavior." Correct alternative: set FK values in an `early_row_event` (fires before the rule engine, before relationships are resolved). **This is the single most relevant documented constraint for relationship-modeling bugs** — if a reported bug involves FK columns being touched by rules, this is the documented (and apparently necessary) workaround, which implies LB's relationship-resolution timing is the root sensitivity.
  - **Sum/Count `where=` clauses:** must not restate FK/PK matching, can only reference child attributes — a documented restriction on what's safe to express, again rooted in how LB resolves parent/child via the relationship (not raw FK comparison)
  - Snapshot (`Rule.copy`) vs live (`Rule.formula` referencing `row.parent.attr`) semantics for parent-value propagation

- **`prototypes/base/docs/training/logic_bank_patterns.md`** (597 lines) — "The Hitchhiker's Guide": event handler signatures, anti-patterns (e.g., FK/monetary typing — FKs must be `int` not `Decimal`, since SQLite integer columns don't support Decimal), the Request pattern, common mistakes (`Rule.count`/`sum`/`copy` don't have `calling=`, event handlers need all three params, etc.)

**Why this matters for LB engine work:** these two files are where GL *teaches* the assumptions an AI (or developer) should hold about how LogicBank resolves relationships, FKs, and parent/child timing. If the GenAI-Logic bug turns out to be a relationship-modeling mismatch, check whether the generated project's model/rules actually followed these documented constraints — and if they did follow them and still hit a bug, the constraint itself (or LB's underlying timing/resolution behavior) is the thing to fix.

**Other relevant pointers:**
- Testing a LogicBank change against real projects requires building locally (`python -m build`) and installing the wheel into the ApiLogicServer BLT venv (see `release-management.md` → Test Installation) — or, for fast iteration, editing the LB package directly under `venv/lib/python3.13/site-packages/logic_bank/` (mirrors the "quick iteration / venv test" pattern GL itself uses for CE — changes are lost on next BLT/reinstall, propagate back to source before that happens)
- `prototypes/basic_demo` has its own (tutorial-flavored) copy of `.copilot-instructions.md` — per GL's CE-drift incident note, `base` is the one that matters; `basic_demo` is a copy, not a source, of LogicBank CE content too

&nbsp;

---

**📖 Remember:** This file provides orientation. Sibling files in `system/LogicBank-Internal-Dev/` will hold additional CE as it's developed (e.g. rule-pattern catalogs, contribution guides).
