---
name: surgical-edits
description: Use when modifying existing code to enforce the smallest correct, review-friendly diff and prevent unrelated changes.
---

# Surgical Edits

Make the smallest correct change and preserve everything else.

## Rules

- Treat the user's requested scope as a hard boundary.
- Modify existing code in place; preserve correct surrounding code and behavior.
- Add, remove, or replace only lines required by the task.
- Preserve names, comments, formatting, ordering, imports, and abstractions unless the change requires otherwise.
- Leave unrelated issues unchanged; mention them only when they materially affect the task.
- Refactor only when explicitly requested or technically necessary.
- Define the expected change surface before editing. If the diff grows unexpectedly, inspect and reduce or justify it.
- For generated files and lockfiles, accept only output required from existing tooling; do not regenerate or upgrade unrelated content.

## Example

Task: add `phone` to the returned user.

```diff
 return {
   name: response.data.name,
   email: response.data.email,
+  phone: response.data.phone,
 };
```

Do not replace the entire function to add this line.

## Diff Check

Before finishing:

- Inspect the final diff.
- Remove delete-and-recreate edits, formatting churn, renames, reordered imports, and unrelated changes.
- Verify every changed line is necessary for the requested result.
