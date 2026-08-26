---
name: concise-coding
description: Use for coding tasks to minimize context, narration, and response tokens without reducing implementation quality.
---

# Concise Coding

Minimize token use without reducing correctness.

## Workflow

- Search for symbols, filenames, and references before opening files.
- Read only relevant ranges; expand context only when evidence requires it.
- Reuse established facts and do not reread unchanged files.
- Stop investigating once evidence is sufficient to act.
- Make only the requested change; omit optional alternatives and improvements.
- Run the smallest validation set sufficient for the change's risk.
- Expand validation only after failures, shared impact, or high-risk changes.
- Never trade correctness or necessary validation for fewer tokens.

## Communication

- Avoid narrating routine tool calls, repeating the request, summarizing files just read, or explaining obvious code.
- Communicate during work only when input, a blocker, a risk, or a scope decision requires it.
- Keep the final response under 10 lines unless more detail is requested or necessary.
- Report only what changed, validation, and any remaining blocker or warning.
