# Project Internals

This document details the parsing and path validation mechanics of the generator.

## Custom Markdown Parsing

We implement a pure Python Markdown-to-HTML parser in `src/parse_md.py` without external dependencies:

- **Block Extraction**: The parser splits files by newlines and extracts code blocks, blockquotes, headers, lists, and paragraphs.
- **List Nesting**: A nesting stack `list_stack` stores tuples of indent levels and list tags (e.g., `(2, 'ul')`) to generate well-formed nested XHTML lists.
- **Inline Parsing**: Sub-expressions are matched using standard regular expressions to parse bold, italic, wikilinks, and images.
- **Code Block Isolation**: Inline code blocks are temporarily replaced with placeholders to prevent formatting syntax from parsing inside backticks.

## Path Calculations & Safety

Orchestrator validation in `src/config.py` enforces constraints:

- **Safety Checks**: The `is_safe_path()` function calls `os.path.commonpath` to ensure target paths are inside the output directory.
- **Permalink Generation**: Vault files generate permalinks as `slugified-name/index.html` to output extensionless relative link paths.
- **Resolver Callback**: The builder passes resolution hooks to `src/parse_md.py` to calculate target directories on the fly.
