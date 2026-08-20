---
name: surgical-edits
description: Enforces minimal, review-friendly code changes. Preserve correct existing code, avoid delete-and-recreate edits, unrelated refactors, formatting churn, and unnecessary diff noise to help reduce token usage.
---

# Surgical Edits

Make the smallest possible code change required to complete the task.

## Core Principle

Preserve existing code whenever it is still correct.

Do not rewrite, recreate, refactor, rename, reorder, or reformat existing code unless the requested change explicitly requires it.

Prefer localized patches over replacing entire blocks.

If the same result can be achieved with a smaller diff, prefer the smaller diff.

## Scope Lock

Treat the user's requested scope as a hard boundary.

Do not fix, improve, modernize, refactor, or clean up adjacent code simply because you noticed an opportunity.

If an unrelated issue is discovered:

- Leave it unchanged.
- Mention it only if it materially affects the requested task.
- Do not include it in the patch unless required for correctness.

A nearby improvement is not part of the task unless the requested change depends on it.

## Minimal Diff

When modifying existing code:

- Change only the lines required by the task.
- Preserve unchanged code exactly when possible.
- Do not delete and recreate unchanged functions, components, objects, or blocks.
- Do not rewrite an entire function when one or two lines can solve the task.
- Do not refactor surrounding code unless necessary for correctness.
- Do not rename existing variables unless required.
- Do not reorder declarations unnecessarily.
- Do not reorder imports unless required.
- Do not change formatting unrelated to the task.
- Do not introduce abstractions unless necessary.
- Do not perform unrelated cleanup.
- Avoid diff noise.

## Diff Budget

Before editing, establish an expected change surface.

For a small task, expect a small diff.

If the resulting diff becomes substantially larger than expected:

1. Stop.
2. Inspect why.
3. Determine whether the extra changes are technically required.
4. Revert unnecessary changes before continuing.

Large diffs require a technical reason, not convenience.

Do not judge generated files only by raw line count; apply the generated-files rules below.

## Backend Example

Existing code:

```js
async function getUser(id) {
  try {
    const response = await api.get(`/users/${id}`);

    return {
      id: response.data.id,
      name: response.data.name,
      email: response.data.email,
    };
  } catch (err) {
    throw err;
  }
}
```

Task:

Add `phone` to the returned user.

Preferred change:

```diff
 return {
   id: response.data.id,
   name: response.data.name,
   email: response.data.email,
+  phone: response.data.phone,
 };
```

Do not delete and recreate the entire function just to add one property.

Avoid:

```diff
-async function getUser(id) {
-  try {
-    const response = await api.get(`/users/${id}`);
-
-    return {
-      id: response.data.id,
-      name: response.data.name,
-      email: response.data.email,
-    };
-  } catch (err) {
-    throw err;
-  }
-}
+async function getUser(id) {
+  try {
+    const response = await api.get(`/users/${id}`);
+
+    return {
+      id: response.data.id,
+      name: response.data.name,
+      email: response.data.email,
+      phone: response.data.phone,
+    };
+  } catch (err) {
+    throw err;
+  }
+}
```

The resulting code may be equivalent, but the second approach creates unnecessary diff noise and may increase generated/reviewed token usage.

## React Example

Existing code:

```jsx
function UserCard({ user }) {
  return (
    <div className="user-card">
      <h3>{user.name}</h3>
      <p>{user.email}</p>
      <Button>Edit</Button>
    </div>
  );
}
```

Task:

Display the user's phone number.

Preferred change:

```diff
 <h3>{user.name}</h3>
 <p>{user.email}</p>
+<p>{user.phone}</p>
 <Button>Edit</Button>
```

Do not rewrite the component, restructure the JSX, change class names, rename props, or modify unrelated elements.

## Existing Functions

When a function already exists, modify it in place.

Do not replace the entire function unless a substantial part of its implementation genuinely needs to change.

Prefer:

```diff
 function calculateTotal(items) {
-  return items.reduce((total, item) => total + item.price, 0);
+  return items.reduce((total, item) => total + item.price * item.quantity, 0);
 }
```

Do not recreate unchanged surrounding code.

## Imports

Preserve existing imports.

Only add or remove imports directly required by the requested change.

Do not reorganize or sort imports as part of an unrelated task.

## Formatting

Respect the existing style and formatting of the file.

Do not:

- Reformat unrelated lines.
- Change quotes unnecessarily.
- Change semicolon style.
- Change indentation unnecessarily.
- Reorder object properties.
- Rewrite equivalent syntax.

Formatting changes are acceptable only when required by the modification or explicitly requested.

## Comments

Preserve existing comments unless they become incorrect because of the requested change.

Do not rewrite comments merely to improve wording.

## Refactoring

Only refactor when:

- The user explicitly asks for a refactor.
- The existing structure prevents the requested change.
- The refactor is required to fix the issue correctly.

When refactoring is necessary, keep its scope as small as possible.

## Generated Files and Lockfiles

Generated files are an exception to strict line-count minimalism.

When a required change updates a generated file such as:

- `package-lock.json`
- `yarn.lock`
- `pnpm-lock.yaml`
- generated schemas
- generated clients
- generated migrations
- other tool-managed artifacts

allow only the changes naturally produced by the project's existing tooling.

Do not manually minimize generated output if doing so could make it inconsistent with its generator.

However:

- Do not regenerate generated files unnecessarily.
- Do not change package manager or lockfile format.
- Do not upgrade unrelated dependencies.
- Do not run commands that rewrite generated files unless required by the task.
- If a generated diff is unexpectedly large, verify why before accepting it.

## Proportional Validation

Validate proportionally to the change.

Prefer the smallest validation set that provides strong confidence.

Examples:

- Small isolated change → targeted test, lint, or typecheck.
- Dependency change → install, relevant tests, build, and relevant audit if applicable.
- Shared infrastructure change → broader test suite.
- High-risk behavior change → broader validation when justified.

Do not run redundant validations that provide no additional confidence.

Do not skip necessary validation merely to reduce tool calls or token usage.

## Before Editing

Before changing a file:

1. Identify the smallest affected area.
2. Determine which existing lines can remain untouched.
3. Define the expected change surface.
4. Modify only the required lines.
5. Preserve surrounding behavior.
6. Avoid collateral changes.

## Diff Check

Before finishing, inspect the resulting diff.

Look specifically for:

- Unchanged lines being deleted and re-added.
- Entire functions replaced for small changes.
- Unrelated formatting changes.
- Unnecessary renames.
- Reordered imports.
- Rewritten JSX or objects without a functional reason.
- Unrelated dependency updates.
- Generated files changed without a clear reason.
- A diff substantially larger than the requested scope.

If an unchanged line appears as deleted and re-added without a technical reason, reduce the diff.

If the diff is larger than expected, justify the extra changes or remove them.

## Token Efficiency

Minimal diffs can help reduce token usage by limiting unnecessary code generation, diff review, and follow-up reasoning.

Token savings are a secondary benefit, not a reason to compromise correctness.

Do not:

- Skip necessary implementation work to reduce tokens.
- Avoid required tests.
- Leave code inconsistent.
- Manually corrupt generated files to make the diff smaller.

Optimize for correctness first, then minimize unnecessary work.

## Final Rule

The ideal patch contains only the changes necessary to satisfy the request.

Treat unnecessary code modifications as a defect.

Smallest scope. Smallest diff. Smallest sufficient validation.
