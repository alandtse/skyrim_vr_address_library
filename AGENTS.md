# AGENTS.md

Guidance for AI coding agents (and human contributors) working in this repository.

## Project snapshot

This repo is the CSV database backing the "Address Library for SKSEVR" mod: a mapping from
stable numeric ids (shared with SE's own community Address Library) to the actual game
addresses those ids resolve to, per Skyrim runtime (SE, AE, VR). `database.csv` is the
hand-maintained source of truth; release CSVs (e.g. `version-1-4-15-0.csv`) and the
published Nexus mod are generated from it by `vr_address_tools.py generate` in the parent
`vr_address_tools` repo, on every merge to `main` via `semantic_release.yml` (which also
handles the Nexus upload — see that workflow for the retry procedure if it fails partway).

Base branch for PRs: **`main`**. Never push directly to `main` — release automation runs
from there on every merge.

## Adding or fixing an id — the actual bar

`README.md` documents the `status` column's confidence scale (0=Unknown through
4=Bit-for-bit-identical) and the row format. In practice:

- **Status 4 requires comparing the whole function's bytes, not a handful of leading
  instructions.** A partial match that happens to look identical for the first several
  instructions is not sufficient evidence — pull the complete byte range for both runtimes
  being compared and diff them.
- **A decompiler's default, auto-inferred signature is not ground truth.** Ghidra's
  calling-convention analysis routinely fails to recognize real parameters (they show up as
  unclaimed `in_EDX`/`in_R8`-style reads) or a real return value (a byte written to `AL`
  right before `RET` with no corresponding `return` in the decompiled output). Verify a
  recorded signature against the raw disassembly, and decompile a real caller too — a
  caller's decompiled call site becomes dramatically clearer once the callee's signature is
  actually complete, which is itself a good cross-check that the fix was correct.
- **New rows go in ascending numeric `id` order, at their actual position — not appended at
  end of file.**
- **CSV quoting must match `csv.QUOTE_MINIMAL`**: quote a `name` field only if it contains a
  comma, quote, or newline; leave it unquoted otherwise. `check-csv.yml`'s bot is *supposed*
  to auto-fix this on every PR touching a `.csv` file, but verify it actually ran (`gh pr
  checks`) rather than assuming — as of this writing it has not run since 2025-09-23. To
  check by hand:
  `python scripts/autofix_csv_quotes.py <changed-file>` and review the diff — but only commit
  the lines your own change actually touched; that script rewrites the *entire* file it's
  pointed at, and this repo's `database.csv` currently carries pre-existing quoting
  inconsistencies elsewhere that are not this PR's problem to fix.
- **`se_ae.csv`** (`sseid,aeid,confidence,name`) maps this project's SE-numbered ids to the
  separate numeric id space AE's own community Address Library uses for the same function.
  New rows follow the same ascending-order rule. Neighboring ids in a cluster often (not
  always — verify, don't assume) share a constant SE-to-AE id offset; treat that as a
  starting hypothesis to check against the actual AE offsets CSV for the specific id, never
  as sufficient evidence on its own.

## Code quality

- **Comments/descriptions state a fact, not a narrative.** A `name` field is a signature, not
  prose about how it was discovered.
- **Minimal churn** — a PR adding or correcting one id touches exactly that row (and, if
  genuinely necessary, its neighbors' ordering) — not an unrelated cleanup pass over the rest
  of the file, even when running a repo tool surfaces other pre-existing issues nearby.

## Constructive proactivity

- Flag a low-confidence entry proactively rather than letting it sit at a status that
  overstates it — say so in the PR body if you can only get to status 2/3, not 4.
- Prefer surfacing a gap (a consuming repo needs an id this database doesn't have yet) over
  silently leaving the consumer to anchor by raw offset.
- **Verify identifying facts; don't confabulate.** An id, an address, a status level, a
  signature — read it from the actual binary/canonical CSV before recording it. A
  plausible-sounding SE-to-AE id-offset pattern is a hypothesis to check, never evidence on
  its own.

## Security

- This repo's `check-csv.yml` runs on `pull_request_target` against PR-supplied content —
  treat any new CI step touching PR-controlled file paths or names with the same care as
  the rest of GitHub Actions hygiene: pass anything workflow-dispatch- or PR-tainted through
  `env:` indirection in a `run:` step, never direct `${{ }}` template interpolation.

## Testing & validation

- **Never bypass commit verification** (`--no-verify` or otherwise skipping pre-commit/
  commit-msg hooks) unless the user explicitly directs it for a specific commit.
- Treat `git commit`/`gh pr create` as a hard checkpoint: re-read this file's Commits & PRs
  section immediately before either.

## Commits & PRs

- Conventional Commits, title ≤ 50 chars. New/corrected ids → `feat:`. Release commits
  (`chore(release): X.Y.Z [skip ci]`) are bot-authored — never hand-write one.
- **`ci` is its own type, not a scope.** A `.github/workflows/*` or CI-config-only change is
  `ci: ...`, never `fix(ci): ...`/`feat(ci): ...` — stacking it as a scope on `fix`/`feat`
  claims a patch/minor release for a change with no user-facing release impact.

## Collaboration / git safety

- Never force-push or rewrite history on `main` without explicit instruction.
- A review sweep must read each review's full body text, not just inline `reviewThreads` —
  "outside diff range" findings are often embedded in the review body with no inline thread.
- Don't manually create release tags or bump version fields — semantic-release owns both on
  merge to `main`.
- If a fix in a *consuming* repo (e.g. `EngineFixesSkyrim64`, `CommonLibVR`) depends on an id
  or mapping this repo doesn't have yet, land the address-library PR here first and reference
  it from the consumer's PR — a `REL::ID()` call for an id missing from the currently-released
  address library aborts the game at load, it doesn't fail soft.
