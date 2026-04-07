---
name: 'Documentation Standards'
description: 'Conventions for writing and updating project documentation'
applyTo: '**/*.md'
---

# Documentation Conventions

- Keep documentation concise and scannable. Prefer tables, bullet lists, and short paragraphs over long prose.
- Use relative Markdown links between docs. Never use absolute filesystem paths.
- When making a significant design decision, record it as an ADR in `docs/architecture/decisions/`.
- When updating code that docs reference, check for docs-drift and update the docs in the same commit.
- New terms should be added to `docs/reference/glossary.md`.
- Open questions go in `docs/reference/open-questions.md` with the standard format.
- Tech debt goes in `docs/reference/tech-debt.md` with the standard format.
- ADRs use the template in `docs/architecture/decisions/README.md` and are numbered sequentially.
