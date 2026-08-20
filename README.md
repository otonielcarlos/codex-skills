# codex-skills

A small collection of skills for Codex focused on reducing unnecessary work, token usage, and diff noise.

The main goal is simple:

**Change what needs to change and leave everything else alone.**

Codex can move quickly through a codebase, but small tasks can sometimes produce larger changes than necessary: rewriting code that was already correct, touching unrelated formatting, running excessive validation, or narrating routine work.

These skills add stricter boundaries around that behavior.

## Goals

* Keep Codex changes small and focused.
* Preserve existing code when it is still correct.
* Reduce unnecessary rewrites and formatting churn.
* Produce cleaner pull requests.
* Make diffs faster to review.
* Reduce unnecessary token usage.
* Keep validation proportional to the change.
* Avoid unrelated cleanup and refactors.

Token savings are a result of reducing unnecessary work. Correctness still comes first.

## Skills

### surgical-edits

Keeps code changes localized and review-friendly.

It tells Codex to preserve correct existing code, stay inside the requested scope, avoid delete-and-recreate edits, and inspect the final diff for unnecessary changes.

A small task should usually produce a small diff.

Instead of:

```text
42 lines changed because the surrounding block was rewritten
```

prefer:

```text
2 lines changed because 2 lines needed to change
```

### concise-coding

Reduces unnecessary conversational output during coding tasks.

Codex can investigate, search, edit, and validate without narrating every routine step.

The final response should normally contain only:

* What changed.
* What was validated.
* A blocker or warning, if one exists.

## Install

Install all skills:

```bash
npx skills add YOUR_USERNAME/codex-skills
```

Install only Surgical Edits:

```bash
npx skills add YOUR_USERNAME/codex-skills --skill surgical-edits
```

Install only Concise Coding:

```bash
npx skills add YOUR_USERNAME/codex-skills --skill concise-coding
```

## Philosophy

Small task. Small diff.

Less unnecessary code generation means less diff noise, less code to review, and potentially fewer tokens spent generating and reasoning about changes that were never needed.

The goal is not to make Codex do less.

The goal is to make it do less **unnecessary** work.

## License

MIT
