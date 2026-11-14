---
name: change
description: 'Make a narrowly scoped adjustment to existing J26_SE_355 behavior or appearance while preserving unspecified functionality. Use for Change: requests; do not expand into feature development or automatically commit.'
---

# Change

Read root `AGENTS.md` and `docs/development-workflow.md` from this repository. Resolve project paths from the repository root, not this skill directory.

1. Inspect current behavior, Git status, relevant tests, and the smallest owning component. State what will change, what must stay the same, and observable **Done when** conditions. For a blue dashboard palette, scope selectors/assets to that dashboard and preserve filters, navigation, data queries, exports, and accessibility.
2. Keep the diff limited to the requested change and unavoidable supporting edits. Avoid unrelated cleanup, dependency upgrades, architectural refactors, changes to another member's component, or altered analytical definitions. If shared code affects other consumers, prefer a scoped option and check those consumers.
3. If completing the request requires an unspecified functional change, describe it concretely: **Existing behavior X would become Y, affecting Z**. Explain why and offer a narrower alternative; wait for the user's decision before making that additional change. A clearly requested X-to-Y behavior change needs no redundant approval.
4. Check security on the changed path. Fix directly related minor issues only when non-breaking. Raise major issues with impact and options before remediation, and pause dependent unsafe work. Record unrelated findings for follow-up rather than silently expanding scope.
5. For logic changes, add or update meaningful regression tests before implementation. Reuse adequate existing tests. For presentation-only changes, use relevant browser/manual checks (including contrast, focus, responsiveness, and unchanged interactions); add tests only when they verify a useful invariant. Document-only changes need document/link verification.
6. Make the smallest maintainable edit. Run affected checks and the main suite/app checks per the shared workflow; run public browser checks for affected dashboard interactions/layout. Review the diff specifically for unintended behavior changes and private/research-data edits. Update only documentation affected by the change and record material unresolved findings.
7. Report the exact change, preserved behavior, checks and limitations, security findings, and any blocked decision. Leave the work uncommitted unless explicitly asked to commit; if asked, follow the shared commit gates and stage only task-owned changes. Never push or deploy implicitly.

If the request grows into new functionality or a broad refactor, explain the scope change and ask whether to switch to the `commit` workflow. Do not switch silently.
