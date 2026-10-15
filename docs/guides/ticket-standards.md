<!-- template-version: 6 -->
<!-- doc-rules-version: 21 -->

# Ticket standards (canonical)

This is the **single source of truth** for what a *ready* work ticket must contain in VPNSentinel.
The five work issue-templates in `.github/ISSUE_TEMPLATE/` (`feature`, `bug`, `security`,
`infrastructure`, `design`) carry the form fields that collect this content; this document holds
the **rules and the rationale**. The `ticket-gate` agent, where installed, enforces the rules.

**This doc carries two markers, and they answer different questions.** `template-version` says
*which form this doc describes*: it is version-locked to the five work templates by
`scripts/check-template-lockstep.sh` (run in CI by `.github/workflows/template-lockstep.yml`), so
the standard cannot silently drift apart from the forms that implement it. `doc-rules-version`
says *which revision the rules text below is at*. A change to the rules that does not change the
form fields bumps **only** `doc-rules-version`.

## Why single-source

The requirement text used to be restated in each template, in `CLAUDE.md`, and in the gate. The
copies drift: prose says one thing while a template says another, and nobody notices until a
ticket is gated against a stale rule. Keeping the rules here, referenced (not restated)
elsewhere, plus the lockstep guard, makes "the standard is the same everywhere" mechanically
true rather than a matter of discipline. (Where the gate restates a rule, the Precedence section
below says which text wins.)

## Required sections

A ready work ticket must satisfy every rule below whose scope the ticket actually touches.
Applicability is decided by the gate from the ticket type and the packages it affects; a rule a
ticket does not touch is marked N/A with a one-line justification, never failed. A rule that
*does* apply and is absent fails the gate.

### 1. GWT scenarios (Given / When / Then)

At least one positive and one negative scenario per independent condition, written against
specific route, module, and dashboard or Telegram message names where the ticket makes them evident. Vague restatements
of the description do not count.

**Scope:** any ticket with an observable behaviour change. The gate derives this from the
ticket type and the areas it affects; the author never self-declares it. N/A is permitted only
where no behaviour delta exists (a pure design mockup, a research spike), and the gate scores that
N/A claim like any other.

**Quality bar** (each point scorable by the gate):

- exactly ONE `When` per scenario; multiple When/Then pairs mean multiple behaviours, split them
- declarative, not click-by-click imperative
- names a real route, module, or message where the ticket makes one evident
- the negative scenario asserts a SPECIFIC error code or message, never "it fails"
- not a restatement of the summary

### 2. Unit test specs

Concrete cases: a specific test file path under `tests/unit/` (for example `tests/unit/test_api_routes.py`), a concrete input value, and the expected output or
error code. "Add unit tests" is not a spec. **When a ticket creates or modifies an API
endpoint** (the Flask routes in `src/vpn_sentinel/common/api_routes.py`), 100% automated coverage
of that endpoint is required, enumerated case by case: happy path; missing or malformed field 400
with a specific message; **no API key 401; invalid API key 401; IP outside the allowlist 403**;
rate-limit enforcement (30 req/min/IP); client isolation (client A cannot overwrite or read client
B's status). A single generic auth test does not satisfy this: the three auth cases are distinct.
New code in `vpn_sentinel.common` must keep the 80% coverage gate green.
Where the change touches shared code, integration and regression coverage is named too.

### 3. E2E test specs

For any behaviour observable through the running stack (dashboard on :8080, API on :5000, health
on :8081, Telegram messages): a specific test file under `tests/integration/`, setup steps, the
action, and the assertion, for both the happy and unhappy paths. These run against the local Docker
stack via `bin/local-env verify`. **Tickets with no running-stack surface (for example pure
refactors or CI-only changes) mark this N/A with justification** rather than inventing a flow.

<!-- adapt-dropped: emulator-clause -->

### 4. Personal data handling

State seven facts, numbered here because the templates, the gate and the `privacy-regime` skill
all count them the same way: (1) every personal-data field the ticket touches (client public IP, geolocation, client
ID, Telegram chat ID); (2) storage location and encryption at rest; (3) erasure, including cascading deletion of
dependent records; (4) portability; (5) minimisation and retention; (6) the legal basis; (7) any
cross-border transfer. A ticket that touches no personal data marks this N/A with that reason.

**This rule names no jurisdiction on purpose.** Those seven facts exist under GDPR, UK GDPR, CCPA
and CPRA, LGPD, PIPEDA and APPI, under different names, different thresholds and different article
numbers. Naming one regime in the default is not merely over-inclusive; for most projects it is the
*wrong* regime, and a gate citing the wrong statute is worse than a gate citing none, because it
looks authoritative. A project that IS under a specific regime installs the privacy-regime lens,
which names its own regime and adds that depth (issue #101).

### 5. Security checklist

Authentication and authorization requirements (API key, IP allowlist), input validation of client-provided data (IPs, kebab-case client IDs, locations), data-exposure review,
and the relevant OWASP Top 10 items for the change. Rate limiting (the API middleware allows 30 req/min/IP) is specified or justified as
unnecessary.

### 6. Required reviews

The reviews the ticket must pass before it is considered done, checked off explicitly. This is
the ticket author's acknowledgement of the gate, not a substitute for it.

### 7. Documentation currency

The ticket names the documentation it affects, in the project's documentation tree and its root
README, or states none with a reason. **Scope is deliberately every work ticket**: this is the
one rule where always-asked is the point. It stays passable because "none, no user-visible
surface" is a legitimate answer, and the gate scores that claim like any other N/A, judged
against the ticket's own file list.

### 8. Implementation and dependency concreteness

Judged against whichever fields the template provides (`implementation`, `dependencies`, `files`),
not a new form field: the templates already collect this content, so this rule adds no section and
no `template-version` bump.

- File paths and implementation steps are concrete, and match the conventions in `CLAUDE.md` (config from `VPN_SENTINEL_*` env vars, route paths derived
  from `API_PATH`, external HTTP calls with retry/fallback).
- Build and test commands the ticket relies on are specified (for example `./tests/run_tests.sh`, `bin/local-env verify`), so an implementer does not guess them.
- Every new dependency is justified against the standard library and the dependencies already
  present.
- Known scalability risks the approach introduces are named: unbounded loops over `client_status`, work done while holding `client_status_lock`, and Telegram message bursts first.

A ticket whose template carries none of these fields (for example `infrastructure`) records N/A by
domain, per the N/A rule below.

## Precedence

The `ticket-gate` agent, where installed, restates parts of this doc so they hold in installs
without it. The gate cites a section here by its TITLE, as `section "Title"` with the title
spelled exactly as the `### N. Title` heading gives it, minus any trailing parenthetical (so
`section "GWT scenarios"`), never by number: this adapted copy may renumber or insert sections, and
a citation like "rule 3" would then point at the wrong one. Keep the heading titles stable; a
renamed heading must be renamed in the gate in the same change.

Where this doc IS installed, its text governs, and three cases are distinguished:

- **Conflict.** The gate's copy and this doc state different things: **this doc wins.** The gate's
  copy is a convenience restatement, never a fork.
- **Absence.** A rule is missing from an installed (possibly adapted-down) copy of this doc: that
  is NOT divergence. Absence never relaxes a gate bar; only explicit text here does.
- **A stricter restatement.** The gate says the same thing at finer granularity than this doc.
  This is neither conflict nor absence, and the extra strictness is **ADVISORY, never blocking**.
  The gate reports it as a gap in this doc, naming the rule, so the fix is to tighten the doc and
  make the bar legitimately blocking. A stricter gate copy must never out-rule this doc silently,
  or the single-source claim is fiction.

Editing a rule here means checking the gate's restatement in the same change.

## The N/A rule (load-bearing)

A coverage or E2E requirement that a docs-only, research, infra-only, or API-only ticket cannot
satisfy makes that ticket **un-passable**, which trains people to box-tick and rots the whole
gate. Every rule here is scoped: it applies only to tickets whose type and affected packages
bring it into play, and the gate derives that scope rather than asking the author to self-declare
it. When you add a new rule with a coverage-style requirement, give it an explicit
type-and-area scope here, or it will backfire.
