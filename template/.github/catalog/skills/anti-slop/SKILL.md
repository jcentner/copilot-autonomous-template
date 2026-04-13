---
name: anti-slop
description: "Detect and fix AI-generated code smells. Use when reviewing code produced by autonomous agents, or proactively after 10+ autonomous slices. Identifies excessive comments, dead code, unnecessary abstractions, and other AI-tell patterns."
---

# Anti-Slop

AI-generated code has recognizable patterns that signal low-quality output. This skill helps detect and fix these patterns to maintain code quality during autonomous development.

## When to Use

- After the reviewer flags AI-generated code smells
- Proactively after 10+ autonomous slices as a quality sweep
- When code feels bloated, repetitive, or over-engineered
- Before a major release or phase completion

## AI Code Smells

### 1. Excessive Comments

**Pattern**: Comments that restate the code.
```
// Bad: AI-slop commenting
const users = []; // Initialize empty users array
users.push(user); // Add user to array
return users; // Return the users
```

**Fix**: Remove comments that don't add information beyond what the code already says. Keep comments that explain *why*, not *what*.

### 2. Over-Abstraction

**Pattern**: Single-use helpers, wrapper functions that add no value, premature generalization.
```
// Bad: Wrapper that does nothing useful
function getFormattedDate(date) {
  return formatDate(date);
}
```

**Fix**: Inline single-use abstractions. Only extract when there are 3+ call sites or the abstraction genuinely clarifies intent.

### 3. Cargo-Cult Error Handling

**Pattern**: Try-catch blocks that catch and rethrow, or handle errors that can't happen.
```
// Bad: Catching errors that can't occur in this context
try {
  const x = 2 + 2;
} catch (error) {
  console.error('Failed to add numbers:', error);
  throw error;
}
```

**Fix**: Only add error handling at system boundaries (I/O, network, user input). Don't wrap pure computation.

### 4. Dead Code

**Pattern**: Commented-out code blocks, unused imports, unreachable branches, functions defined but never called.

**Fix**: Delete it. Version control exists for a reason.

### 5. Verbose Variable Names

**Pattern**: Names so long they hurt readability.
```
// Bad
const userAuthenticationTokenExpirationTimestamp = Date.now();
```

**Fix**: Use concise names that are clear in context: `tokenExpiry`, `authExpires`.

### 6. Defensive Duplication

**Pattern**: The same validation or check performed at multiple layers because the AI wasn't sure which layer was responsible.

**Fix**: Validate once at the system boundary. Internal functions can trust their callers within the module.

### 7. Template-Speak in Docs

**Pattern**: Documentation that reads like a prompt response: "This module provides a comprehensive solution for..." or "This function is responsible for handling the complex process of..."

**Fix**: Write like a human developer. Direct, specific, no filler.

### 8. Symmetry Obsession

**Pattern**: Creating matching pairs when only one side is needed. Making every `create` have a `delete`, every `get` have a `set`, even when the counterpart has no use case.

**Fix**: YAGNI. Build what's needed now.

## Review Checklist

Run this checklist against recently-written code:

- [ ] **Comments**: Remove any comment that restates the code. Keep only why-comments.
- [ ] **Abstractions**: Find functions called from only one place. Consider inlining.
- [ ] **Error handling**: Find try-catch blocks. Can the caught error actually happen?
- [ ] **Dead code**: Search for TODO/FIXME/HACK comments, commented-out blocks, unused imports.
- [ ] **Naming**: Find variable names with 4+ words. Can they be shorter without losing clarity?
- [ ] **Validation**: Find the same input validated in multiple places. Consolidate to boundary.
- [ ] **Docs**: Read doc comments aloud. Do they sound like a person or a template?
- [ ] **YAGNI**: Find code that exists for a "future need." Is that need in the current phase plan?

## Output

Report findings as:

| Pattern | File | Lines | Description | Fix |
|---------|------|-------|-------------|-----|
| Excessive Comments | path | L10-25 | 15 inline restating-the-obvious comments | Delete |
| Over-Abstraction | path | L40 | `wrapResponse()` called once, wraps `res.json()` | Inline |

Then provide total count by pattern and an overall slop score: Clean / Mild / Moderate / Heavy.
