# Project development workflow

This is the shared working agreement for incremental development of J26-SE-355. Its goal is trustworthy technical-skill research and a separate, read-only public dashboard. Preserve team ownership and research evidence while delivering small, verifiable changes.

## Request modes

| Request | Expected action | Scope and finish |
| --- | --- | --- |
| `Commit: <outcome>` | Use [commit](../.agents/skills/commit/SKILL.md). Assess the idea, define done, test first, implement, review security, validate, document, and commit locally. | Allows directly related minor non-breaking cleanup; no implicit push or deployment. |
| `Change: <adjustment>` | Use [change](../.agents/skills/change/SKILL.md). Modify only the requested existing behavior or appearance. | Preserve unspecified functionality; leave uncommitted unless asked. |
| `What's the next step?` | Inspect current goals, backlog, code, and available verification evidence. Propose one bounded next outcome. | Planning only; describe open security/testing issues and a Done when contract. |
| `Go ahead with committing the next step` | Execute the most recently agreed, unambiguous next-step contract using `commit`. | Local commit is authorized; ask only if the referent or a consequential decision is unclear. |

The skills live under `.agents/skills/` so they travel with the project. Root `AGENTS.md` routes the natural-language prefixes; `$commit` and `$change` can also invoke discovered skills. A newly added skill may need a fresh chat to appear in the skill picker; the repository routing instructions still identify the files to read.

## Before implementation: done means observable outcomes

State a short task contract in the chat before coding. Routine tasks do not require an approval round. Challenge a questionable idea before implementation and explain how it affects the project goals. Ask when the answer changes research meaning, a public contract, data safety, team boundaries, or a major security decision.

Use this template, scaled to the task:

```text
Outcome: what the user will be able to do, or the defect that disappears.
Scope: owning modules and any unavoidable shared changes.
Preserve: existing behavior/contracts that must remain intact.
Done when:
- Observable acceptance examples and relevant edge cases pass.
- Meaningful regressions demonstrate the intended change.
- Affected checks and required broader checks pass; limitations are explicit.
- Changed security boundaries are reviewed and major decisions resolved.
- Relevant docs/backlog reflect the result, with no incidental research-data edits.
- For Commit: only task-owned changes are committed locally and verified.
```

For example, a temporal eligibility fix is done when an insufficient-sample interior month stays excluded, a genuine eligible zero remains zero, monthly/quarterly boundary regressions pass, and the documentation states the preserved denominator policy. A dashboard palette change is done when the requested dashboard uses the palette with readable contrast and focus states at desktop/mobile widths, and existing filters, navigation, URLs, downloads, and data results retain their behavior.

Acceptance conditions can be refined when new evidence emerges, but explain material changes. Do not drop a condition merely because it is difficult or a test fails. Documentation-only work uses document/link review and skill validation where applicable, rather than artificial tests of prose.

## Test and review gates

For behavioral work, establish a failing acceptance/regression test before implementation and verify that it fails for the intended reason. Implement the smallest sound solution, then run it again. Keep network access mocked, fixtures offline, and databases temporary. Do not exercise imports or publishers against the tracked master as a side effect of verification.

Use the existing isolated interpreter. On Windows, activation is optional; `.venv\Scripts\python.exe` can replace `python`. Run affected tests first, then:

```powershell
python -X utf8 -m unittest discover -s tests -p "test_*.py"
python -X utf8 -m unittest src/test_app.py
```

Discovery under `tests/` does not cover every source-local or pytest test. Run those relevant to the changed component. For public dashboard changes, also use:

```powershell
python -m unittest discover -s tests -p "test_public_dashboard.py"
python tests/browser_public_dashboard.py
```

Browser checks apply when dashboard appearance, interactions, or browser contracts change. Capture screenshots for dashboard review. Do not install heavyweight optional tools or run live collection merely to verify a documentation edit. Report missing tools, skips, actual failures, and checks not run accurately.

Historical failures are recorded in [suggestions.md](suggestions.md), including an OCR import failure, a DNS-sensitive validator check, and an unverified Docker build. These are leads for investigation, not current test results or automatic waivers. Reproduce/compare failures safely if they affect the completion decision. A regression introduced by this task blocks completion. An unrelated baseline failure should be documented with evidence and a follow-up; do not repair a teammate's component incidentally. A commit may proceed with a demonstrated unrelated baseline failure when all affected checks and the task's Done when conditions pass; disclose the failure and evidence in the handoff. If a failure's relationship to the change is uncertain, an affected check is unavailable, or an agreed condition requires a fully green suite, report the blocker and obtain explicit acceptance of that specific limitation before committing. Never describe a partial or failing run as a green codebase.

Review the final diff against the task contract, including shared callers, public API behavior, analytical definitions, dependencies, secrets, and data files. Use `git diff --check` for patch hygiene. Passing checks supports a bounded claim; it cannot guarantee absence of defects or validate the research sample.

## Security and research boundaries

- Preserve URL validation, redirect/subresource safeguards, crawling limits/delays, and TLS certificate verification. Do not bypass source access restrictions. Use offline fixtures for boundary regressions.
- Keep the master database, raw job text/URLs, private identifiers, admin tools, and ML dependencies outside the public runtime/publication. Preserve read-only access, reviewed matched cohorts, zero-skill records, and synthetic provenance.
- Review affected input/output handling, including SQL parameters, rendered content, downloads, resource limits, filesystem paths, and configuration, where relevant to the task.
- Fix directly related minor non-breaking issues proactively in `Commit:` mode. `Change:` mode has a stricter scope: only necessary, directly related supporting fixes belong in its diff.
- A major issue includes possible sensitive-data exposure, destructive migration, a weakened security boundary, or a remedy that materially changes compatibility, research meaning, dependencies, or another member's component. Explain the evidence, impact, proposed remedy, and alternatives; ask before that remediation and pause dependent unsafe work. Continue independent authorized work.

Track an unresolved finding in the existing relevant backlog with its location, impact, evidence/status, proposed next action, and owner if actually known. Separate a confirmed defect from a suspicion or old report. Never invent an owner or imply that documentation has fixed code.

## Team boundaries and Git

Inspect status and existing staged changes before editing. Follow established module ownership where documented; do not infer ownership from a filename or rewrite adjacent components for consistency. Necessary shared changes should be small, explained, and verified against their callers. Ask if a change materially alters another member's contract.

Stage explicit task-owned files/hunks and inspect the staged diff. Preserve other work, including pre-existing staged changes. If ownership cannot be safely separated, stop and ask rather than including or discarding it. Keep hooks enabled. Use an outcome-focused Conventional Commit subject (`feat:`, `fix:`, `docs:`, `chore:`, or `refactor:`, with optional scope) and explain material rationale/limitations in a body when useful. Verify the commit and report remaining changes. Local commit authorization does not authorize push, merge, deployment, destructive Git operations, or history rewriting.

## Choosing and recording the next step

When asked for the next step, read [About.md](About.md), the relevant portions of [suggestions.md](suggestions.md), recent task records, Git status, and owning code/tests. Prefer the smallest outcome that advances reliable research or resolves a blocking security/correctness issue. Explain dependencies and team boundaries; do not mechanically take the next numbered backlog item.

Return one recommendation with:

- The feature/fix and its user or research value.
- Proposed scope and an observable Done when contract.
- Relevant open security and testing issues, distinguishing verified findings, older reports, and checks not yet run.
- Any prerequisite decision, ownership coordination, or blocker.

End the reply with a **Suggested commit** section and one fenced `text` block containing a ready-to-send `Commit:` prompt. Include the recommended outcome, bounded scope, important preserved behavior, observable Done when conditions, and any intentional behavior change the user would be approving. Make the prompt self-contained enough to use in a later chat; do not rely on phrases such as "do the above." Keep unrelated security/testing findings in the surrounding recommendation instead of bundling them into the proposed commit. If a prerequisite decision is unresolved, state it in the prompt and require resolving it before dependent implementation.

The section is a prompt for the user, not a proposed Git commit subject. For example:

```text
Commit: Make the collection HTTP client fail clearly on TLS certificate errors instead of retrying without verification. Limit changes to the client, necessary caller handling, offline tests, and related docs. Preserve URL/redirect validation, crawling delays, response limits, and valid-source behavior. Invalid-certificate sources should stop collecting until their certificate or local trust configuration is corrected. Done when certificate failures never trigger an unverified retry, offline regressions cover failures/verified redirects/success, affected checks pass, and full-suite results and any unrelated baseline failures are documented. Finish with a local commit.
```

This recommendation does not authorize coding. Once the user approves committing that step, proceed without asking again for routine implementation or the final local commit. A newly discovered major decision still needs the user's input.

At task completion, update the relevant backlog entry or add a concise dated outcome there when useful: what changed, validation evidence, and unresolved follow-ups. Update README/component guides when their behavior changes. Do not rewrite other members' guides or mark a broad issue complete based on a narrow fix. Keep this workflow as the stable agreement; current work and known issues belong in the backlog.

## Making requests more precise

An outcome, one concrete example, and a Done when condition are usually enough. Mention constraints or component ownership when known. For a narrow change, name the target screen/component and behavior to preserve. Avoid combining unrelated features into one commit; let the next-step recommendation expose dependencies instead.
