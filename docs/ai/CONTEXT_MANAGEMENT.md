# Context Management — Travel Concierge

Use this to avoid bloated Claude chats and degraded adherence.

## Start a new Claude chat when

- Starting a new phase, architecture slice, or Level 2/3 task.
- The current chat has already produced a PR and follow-up fix.
- The task touches multiple contracts or providers.
- Prior context includes stale assumptions or failed patches.
- A clean PR summary/audit is more valuable than chat continuity.

## Follow up in the same chat when

- The PR is open and the fix is a narrow reviewer change.
- The change is a typo, missed test, or small docs correction.
- Claude needs to update the same PR based on fresh ChatGPT review.

## Stop after PR summary when

- Usage is Medium-High or High.
- The PR is opened and self-audit is complete.
- Further work would belong to a new task or phase.

## Compacting rule
If compaction is needed, preserve only:

- current repo/branch/PR
- task goal and severity
- assumptions and success criteria
- files changed
- tests run/results
- known risks/limitations
- next required action

Do not preserve long implementation narration unless needed for review.
