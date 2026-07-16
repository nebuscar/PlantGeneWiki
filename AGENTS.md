# PhytoAtlas Agent Instructions

## Communication

- Always respond in Simplified Chinese.
- Explain the purpose, logic, validation, and remaining risks of each change.

## Code style

- Do not add redundant process output.
- Do not add redundant blank lines.
- Use concise English code comments only.
- Separate key script stages with numbered long headings such as `########## 0. params ##########`.

## Engineering boundaries

- Read existing code and schemas before editing.
- Keep changes scoped to the assigned role and task.
- Do not commit credentials, `.env` files, raw data, generated indexes, or internal server paths.
- Do not treat vector similarity as a verified biological relation.
- Do not bypass normalization to read raw source data from the API or frontend.
- Preserve user changes and unrelated dirty worktree content.
- Run focused tests before reporting completion.

## Multi-agent collaboration

- The root task owns decomposition, integration, and final acceptance.
- Concurrent write tasks must use separate Git worktrees.
- Read-only audits may run in parallel in the main worktree.
- Every subagent report must list changed files, validation results, unresolved issues, and risks.
