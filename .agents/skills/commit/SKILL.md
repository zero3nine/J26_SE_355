---
name: commit
description: 'Implement a project feature or fix through tests, security review, validation, documentation, and a local Git commit in J26_SE_355. Use for Commit: requests or explicit approval to commit an agreed next step; not for narrowly scoped Change: requests.'
---

# Commit

Read root `AGENTS.md` and `docs/development-workflow.md` from this repository before working. Resolve project paths from the repository root, not this skill directory. Use the current goals in `docs/About.md` and relevant backlog evidence in `docs/suggestions.md`; inspect owning code before treating old findings as current.

## Establish the outcome

- Inspect Git status, staged changes, applicable instructions, callers, tests, and the affected component. Preserve teammates' edits and component ownership.
- Assess the idea before implementation. Challenge proposals that undermine research validity, privacy, maintainability, or the public/research boundary; explain a concrete alternative. Ask early when a consequential decision is unresolved; continue independent authorized work.
- State a small scope and observable **Done when** conditions before coding. Include intended behavior, important preserved behavior, tests, security boundaries, and documentation. Use reasonable defaults for routine choices without requiring plan approval.
- When the request comes from a **Suggested commit** prompt, use its scope, preserved behavior, intentional changes, and Done when conditions as the task contract. Recheck current code and blockers; do not expand it to unrelated findings listed in the earlier next-step recommendation.
- Implement the requested outcome with directly related, minor, non-breaking fixes and architectural cleanup. Explain additions and keep them bounded. Record unrelated improvements for later instead of taking over another member's component.

## Tests, implementation, and security

1. For behavior changes, write or adjust meaningful acceptance/regression tests first. Run them and confirm failure demonstrates the missing behavior, rather than an import/environment error. Then implement and run them again. Existing tests may already establish a reproducer; report that evidence. For documentation-only or purely visual work, use appropriate document/manual/browser verification rather than artificial tests.
2. Keep transformations in the appropriate `src/` module, persistence in `src/database/`, and UI code focused on presentation. Preserve existing public contracts unless the requested outcome explicitly changes them.
3. Review the changed path and its inputs/outputs for security concerns using the shared workflow's project boundaries. Fix minor non-breaking issues within scope and add regressions where meaningful. For a major issue, explain impact, affected behavior, options, and your recommendation, and ask the user before implementing the major remediation. Do not finalize a commit whose changed path remains unsafe pending that decision.
4. Run affected tests, the main unittest suite, and app checks as described in the shared workflow. Run relevant pytest/source-directory tests and public browser checks when affected. Inspect failures; compare pre-existing failures using safe isolation when needed. Do not weaken tests to obtain a pass.
5. Review the diff for regressions, scope creep, accidental research-data changes, exposed private data, and unnecessary dependencies. Update relevant documentation and backlog entries with actual evidence. Do not claim research validity or comprehensive security from passing software tests.

## Finish with a local commit

- Check each Done when condition. If requirements or required validation remain blocked, report the exact blocker; do not represent the task as done or silently lower the conditions. Apply the shared workflow's baseline-failure rule.
- `Commit:` and explicit approval to commit an agreed next step authorize a local Git commit once gates pass. Do not ask for redundant confirmation. They do not authorize push, deployment, merge, or history rewriting.
- Inspect status and staged diff. Stage only this task's files/hunks with explicit paths. Never sweep in pre-existing staged work; isolate your changes safely or ask if ownership cannot be resolved. Do not reset, stash, overwrite, or amend teammates' work.
- Use a concise Conventional Commit subject describing the outcome, such as `fix(temporal): preserve excluded periods`. Add a body for material rationale or limitations. Preserve hooks; investigate failures and stop if unresolved instead of bypassing them. Verify the resulting commit and remaining working-tree status.
- Report the commit hash/subject, resulting behavior, validation results and limitations, resolved/deferred security issues, and any relevant follow-up. Distinguish task completion from wider project readiness.
