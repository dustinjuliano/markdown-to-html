# Architectural Design Document

This document captures the detailed architecture, core layout strategies, file routing structures, configurations, and test designs of the static site generator.

## 1. Project Goal & Overview

The system outlines a zero-dependency, pure Python static site generator. It ingests an Obsidian vault directory structure containing Markdown files and image assets, processes the content via a custom state-machine Markdown parser, and compiles static HTML files utilizing XHTML5 layout templates and a JSON routing configuration.

## 2. Core Architecture Separation

The codebase logic is strictly divided between parsing stages and orchestration:

- `main.py`: Acts as the command-line entry point to load the default `site.json` configuration and trigger the compilation system.
- `src/central.py`: Serves as the central orchestrator that traverses the vault directory, computes slugified permalink paths, copies image assets, and writes the compiled files to disk.
- `src/config.py`: Loads and parses `site.json`, enforces validation rules, and ensures absolute path safety against directory traversal attacks.
- `src/parse_md.py`: Implements a zero-dependency custom state-machine Markdown-to-HTML parser to process inline formatting and list nesting depths.
- `src/template.py`: Uses the native `xml.etree.ElementTree` library to ingest layout XHTML5 templates, locate `<template>` wrapper hooks, insert dynamic headers and contents, and format output HTML.
- `src/codegen.py`: Functions as the compiler stage that synthesizes raw Markdown inputs and XHTML layout templates in-memory without contacting the disk.

## 3. Configuration & Routing Format

The build pipeline settings are parsed and validated by `src/config.py`. Space characters in vault file names are slugified (replaced with hyphens) and URLs are strictly lowercased.

- **Explicit Routes Mapping**: Configures explicit routing parameters mapping specific folders in the vault to output paths. If no path matching rule exists, default fallback paths apply.
- **Template Mapping Configuration**: Dictates template files used for pages based on vault directory prefixes, defaulting to a base layout.
- **Image Mapping Targets**: Configures default destinations and subfolder overrides for image copy outputs.

### Example `site.json`
```json
{
  "source_vault": "./vault",
  "target_site": "./public",
  "templates": {
    "source_dir": "./templates",
    "mapping": {
      "Articles/": "articles_layout.html",
      "default": "layout.html"
    }
  },
  "routes": [
    {
      "source": "Articles/",
      "target": "articles/"
    },
    {
      "source": "Projects/Active/",
      "target": "projects/"
    },
    {
      "source": "/",
      "target": "/"
    }
  ],
  "image_mapping": {
    "global_target": "assets/img",
    "overrides": {
      "Articles/": "articles/img"
    }
  }
}
```

### Permalink URL Scheme
To support modern clean routing (hiding the `.html` extension), files are output as `target/slugified-name/index.html`.

## 4. Custom Markdown Parser

The custom Markdown parser in `src/parse_md.py` does not depend on any third-party markdown libraries:

- **Inline Parsing**: Processes bold `**bold**`, italics `*italics*`, and inline code `` `code` `` using regular expression replacements.
- **Wikilinks**: Handles Obsidian links format `[[target|Alias]]` and maps them to `<a href="transformed-target/">Alias</a>`. Links without aliases default to the target name as the display text.
- **Image Embeds**: Translates `![[image.png]]` to HTML `<img>` elements, resolving paths using the configuration's global target and override rules.
- **Block Parsing**: Extracts `# Headers`, block quotes, list item depths (`- Lists`), numbered lists (`1. `), and fenced code blocks without syntax highlighting.
- **List Nesting resolution**: Tracks nested lists using a state stack containing indentation levels to produce properly closed XHTML tags.

## 5. Server-Side XHTML5 Templating

The layout compiler inside `src/template.py` relies on XHTML5 templates to operate without external dependencies:

- **Strict XML Rules**: Source templates must be well-formed XHTML with fully closed tags, self-closed void tags (e.g. `<img />`), and quoted attributes.
- **Native DOM Modification**: The template engine recursively parses the template tree, matches `<template>` nodes by their `id` attributes (matching `title` and `content`), injects generated nodes, and strips the wrapper tags. No custom string splitting or regex parsing is utilized for layouts.
- **indentation & Clean Serialization**: Prior to writing output, the tree is normalized with a 2-space indentation via `xml.etree.ElementTree.indent` (available in Python 3.9+ with `space="  "` parameter). The tree is then serialized using `xml.etree.ElementTree.tostring(root, method="html")` to produce standard static HTML5.

## 6. Directory Structure Mapping

Below are the mapped visual representations of the directories:

### Source Vault Folder Tree (`./vault/`)
```text
vault/
├── Home Page.md
├── Articles/
│   ├── My First Article.md
│   └── header_image.png
└── Projects/
    └── Active/
        └── Project One.md
```

### Generated Site Folder Tree (`./public/`)
```text
public/
├── home-page/
│   └── index.html             (uses layout.html)
├── assets/img/
├── articles/
│   ├── my-first-article/
│   │   └── index.html         (uses articles_layout.html)
│   └── img/
│       └── header_image.png
└── projects/
    └── project-one/
        └── index.html         (uses layout.html)
```

### Codebase Repository Structure
```text
/
├── main.py
├── site.json
├── doc/                # Project Documentation
│   ├── design.md
│   ├── internals.md
│   ├── reference.md
│   └── tutorial.md
├── src/
│   ├── central.py      # Central orchestrator / I/O
│   ├── codegen.py      # Core generation logic (Markdown to HTML)
│   ├── parse_md.py
│   ├── config.py
│   └── template.py
└── test/
    ├── mock_vault/     # Permanent mock directory for integration tests
    ├── mock_templates/ # Permanent mock templates
    ├── unit/
    │   ├── test_parse_md.py
    │   ├── test_config.py
    │   └── test_template.py
    └── integration/
        └── test_central.py
```

## 7. Edge Cases & Defensive Programming

The generator enforces strict stability boundaries to ensure robust processing:

- **Path Traversal Protection**: Enforces strict directory limits on file paths from the configuration using `os.path.commonpath` checks.
- **Circular Transclusion Guard**: Tracks a `seen_files` set during build execution to prevent infinite loops in the event of cyclical transclusions.
- **Duplicate Image Prevention**: Halts compiler execution and raises a `BuildError` immediately if duplicate image filenames exist in different directories of the vault.
- **XML Injection Sandbox**: Using `ElementTree` to reconstruct the XHTML DOM acts as a sanitization layer protecting against raw markup injections.
- **Fail Early Strategy**: Manually validates all required schema definitions (`source_vault`, `target_site`, `templates`, and `routes`) and halts operations immediately if layouts fail strict XML checks.

## 8. Verification & Observability Plan

### Observability
All warnings, execution logs, and build summary statistics are output directly to `stdout`.

### Testing Strategy
Testing is separated into isolated unit tests and full integration test suites:

- **Unit Tests**: Contained in `test/unit/` to validate regex parsing in `test_parse_md.py`, configuration structures in `test_config.py`, and XHTML DOM injections in `test_template.py`.
  - `test_parse_md.py`: Asserts markdown (bold, lists, nested blocks, code blocks) and Obsidian wikilinks evaluate to expected HTML strings.
  - `test_config.py`: Validates the JSON schema, template mapping resolution, and URL slugification.
  - `test_template.py`: Validates `ElementTree` traversing, 2-space indentation injection, and `<template>` replacement.
- **Integration Tests**: Contained in `test/integration/test_central.py` to compile the mock directories (`test/mock_vault/` and `test/mock_templates/`) end-to-end and assert correct asset copies, link updates, and layout applications.
  - `test_central.py`: Validates the system end-to-end using the permanently maintained mock structures. This avoids thrashing the disk with temporary file operations, and the test files are heavily commented. Asserts that the orchestrator properly delegates to `codegen`, correctly maps vault files to their respective templates, and writes the final permalink-style structures.
