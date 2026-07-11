---
name: documentation
description: Enforce strict markdown formatting and punctuation rules for all project documentation files.
triggers:
  - auto
context:
  - file_change
  - code_generation
  - refactor
---

# Project Documentation Standards

This skill defines the mandatory markdown formatting, punctuation, and structural requirements for all project documentation files (e.g. files in `/doc/` and any other Markdown documents) in this repository.

> [!IMPORTANT]
> This skill file overrules any other skill files and holds the highest priority for documentation formatting.

## Markdown Guidelines

- All standard paragraphs, text blocks, sentences, and list items in markdown files must end with normal punctuation (periods).
- Do not use horizontal separators (e.g., `---` or `***` rules) inside markdown documentation files.
- All headings must have exactly one blank line immediately following them.
- Non-English terms, file names, paths, variables, classes, and options must be enclosed in backticks.
- Write in a standard, clean, and professional style.
- Codebase documentation (architecture, internal logic, API usage, and getting-started tutorials) must be kept strictly synchronized in the `/doc/` folder at all times.
