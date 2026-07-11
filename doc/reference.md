# Configuration & API Reference

This document provides a comprehensive, self-contained reference for the JSON configuration schema, the XHTML5 template formats, the public module APIs, and the supported Markdown syntax.

## 1. JSON Configuration Schema (`site.json`)

The build pipeline behavior is governed by a configuration file, which defaults to `site.json` in the root repository.

### Configuration Properties

- `source_vault` (`str`, Required): The relative or absolute directory path to the source Obsidian vault containing Markdown files and image assets.
- `target_site` (`str`, Required): The relative or absolute directory path where compiled static files and copied assets will be written.
- `templates` (`dict`, Required): Configuration block detailing layouts:
  - `source_dir` (`str`, Required): The directory containing layout XHTML files.
  - `mapping` (`dict`, Required): Map of vault prefix subfolders to template files. Must include a `"default"` key defining the default fallback template.
- `routes` (`list`, Required): List of routing definition objects containing:
  - `source` (`str`, Required): Subfolder in the vault.
  - `target` (`str`, Required): Subfolder in the output static site.
- `image_mapping` (`dict`, Required): Control block for image copying:
  - `global_target` (`str`, Required): The default destination path inside the output directory.
  - `overrides` (`dict`, Optional): Subfolder-specific override prefixes for image destinations.

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

## 2. Template Specifications (XHTML5)

To bypass external dependencies, layout templates are processed as XML trees via the native `xml.etree.ElementTree` parser.

### Template Injection Hooks

Two `<template>` placeholder tags are replaced at compile time:

| Tag | Replaced with |
|---|---|
| `<template id="title">` | The page title extracted from the note's first `#` heading |
| `<template id="content">` | The compiled XHTML body of the note (everything after the first heading) |

Both placeholders can appear multiple times in the template (e.g. once in `<title>` and again in `<h1>`).

### Template Formatting Rules

- All templates must be strictly well-formed XHTML.
- Standard void tags must be explicitly closed (e.g. `<meta charset="UTF-8" />` or `<img src="..." />`).
- Element attributes must be enclosed in quotes (e.g. `<html lang="en">`).
- The engine formats output with `xml.etree.ElementTree.indent(tree, space="  ")` before writing.
- Output is serialized with `xml.etree.ElementTree.tostring(root, method="html")`, which converts XHTML self-closed void tags back to HTML5 form (e.g. `<img />` becomes `<img>`).

## 3. Public API Reference

The compilation engine exposes several public APIs divided by concerns.

### `src/config.py`

#### `load_config(config_path: str) -> dict`
- **Description**: Loads, parses, and validates the configuration options in a JSON file.
- **Parameters**:
  - `config_path` (`str`): Path to the target JSON configuration file.
- **Returns**: Validated configuration dictionary.
- **Raises**: `ConfigError` if keys are missing or type checks fail.

#### `is_safe_path(base_dir: str, target_path: str) -> bool`
- **Description**: Verifies that a target path lies within a base directory boundaries.
- **Parameters**:
  - `base_dir` (`str`): The root directory constraint.
  - `target_path` (`str`): The absolute or relative path to check.
- **Returns**: `True` if the path lies within the boundaries, `False` otherwise.

### `src/parse_md.py`

#### `parse_markdown(text: str, link_resolver: callable, image_resolver: callable) -> str`
- **Description**: Converts block-level Markdown blocks into XHTML compliance structures.
- **Parameters**:
  - `text` (`str`): Raw markdown contents.
  - `link_resolver` (`callable`): Callback function to resolve relative wikilink target paths.
  - `image_resolver` (`callable`): Callback function to resolve image asset destination paths.
- **Returns**: Generated block-level XHTML string.

#### `parse_inline(text: str, link_resolver: callable, image_resolver: callable) -> str`
- **Description**: Parses inline markdown segments to HTML.
- **Parameters**:
  - `text` (`str`): Raw inline text to compile.
  - `link_resolver` (`callable`): Callback resolving relative links.
  - `image_resolver` (`callable`): Callback resolving image links.
- **Returns**: Formatted inline HTML string.

### `src/template.py`

#### `render_template(template_content: str, title: str, content_html: str) -> str`
- **Description**: Parses the template layout as XML and replaces hook targets.
- **Parameters**:
  - `template_content` (`str`): Raw XHTML template string.
  - `title` (`str`): Document title to insert.
  - `content_html` (`str`): Compiled block-level HTML content to insert.
- **Returns**: Serialized HTML5 string with a prepended doctype.

### `src/codegen.py`

#### `generate_html(markdown_text: str, template_content: str, title: str, link_resolver: callable, image_resolver: callable) -> str`
- **Description**: Serves as the compilation step, synthesizing parsing and template logic in-memory.
- **Parameters**:
  - `markdown_text` (`str`): Input markdown text.
  - `template_content` (`str`): Layout XHTML template.
  - `title` (`str`): Target document title.
  - `link_resolver` (`callable`): Resolver callback for links.
  - `image_resolver` (`callable`): Resolver callback for images.
- **Returns**: Final merged static HTML string.

### `src/central.py`

#### `build_site(config_path: str) -> None`
- **Description**: Orchestrates the entire scan, build, copy, and output pipeline.
- **Parameters**:
  - `config_path` (`str`): Path to the `site.json` file.
- **Raises**: `BuildError` if duplicate image filenames exist in different vault directories.

## 4. Supported Markdown Syntax

The parser in `src/parse_md.py` supports a custom, clean subset of Markdown syntax:

- **Headers**: Supports levels 1 through 6. Heading levels map one-to-one to their HTML counterparts (`#` becomes `<h1>`, `##` becomes `<h2>`, etc.). The first `#` heading in a note is consumed by the compiler as the page title and stripped from the body, so note body sections should conventionally start at `##`.
- **Blockquotes**: Prefixed with `> ` (e.g. `> Quoted text block`).
- **Standard Lists**: Bulleted lists using `- ` prefix.
- **Numbered Lists**: Ordered lists using `1. ` prefix.
- **Nested Lists**: List items indented by spaces relative to their parent list elements.
- **Fenced Code Blocks**: Encapsulated within code fences (e.g. ` ``` `). Code is escaped and placed in `<pre><code>` blocks.
- **Bold Text**: Encapsulated within double asterisks (e.g. `**bold**`).
- **Italic Text**: Encapsulated within single asterisks (e.g. `*italics*`).
- **Inline Code**: Encapsulated within single backticks (e.g. `` `code` ``). Text is protected during inline parsing.
- **Obsidian Wikilinks**: Links enclosed in double brackets (e.g. `[[Target Note|Custom Alias]]` or `[[Target Note]]`). Resolves to relative targets pointing directly to `index.html` files. If no custom alias is provided, the link text displays as the clean filename of the target note, stripping folder prefixes and the `.md` extension.
- **Obsidian Image Transclusions**: Images enclosed in brackets (e.g. `![[image.png]]`). Resolves to configured asset routes.
