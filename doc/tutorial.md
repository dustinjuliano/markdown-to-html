# Getting Started Tutorial

This tutorial provides a comprehensive walkthrough to configure, author, and compile a static website using this tool. The compiler is a zero-dependency, pure Python static site generator that transforms a standard Obsidian vault of nested Markdown notes and image assets into a fully portable, template-driven HTML website.

## 1. How It Works

The compiler reads your Obsidian vault, compiles each Markdown note into an HTML page, and writes the output to a target directory. Three things happen per note:

1. The **page title** is extracted from the first heading (`# Title`) in the Markdown file.
2. The **note body** (everything after the first heading) is compiled into XHTML.
3. The title and compiled body are **injected into an HTML layout template** to produce the final page.

The output site is fully portable — all links are relative paths, so it runs correctly whether served from a web server or opened directly from the filesystem.

## 2. Vault Directory Layout

Notes can be organized in any nested folder structure. Images can live anywhere in the vault, including a dedicated shared attachments folder completely separate from the notes that reference them. The compiler resolves image paths by scanning the vault recursively.

### Example vault structure

```text
vault/
├── Home Page.md
├── Articles/
│   ├── Learning HTML.md
│   └── Introduction to CSS.md
├── Projects/
│   └── Active/
│       ├── Project One.md
│       └── Project Two.md
└── attachments/
    ├── html5-logo.png
    └── css3-badge.png
```

Images in `attachments/` are cleanly separated from the note content. Notes reference them by filename alone using `![[html5-logo.png]]`, and the compiler locates them automatically regardless of vault depth.

## 3. Authoring Notes

Each note must start with a level-1 heading. The compiler strips this heading from the note body and uses it as the page title and HTML `<h1>`.

### Example note: `Articles/Learning HTML.md`

```markdown
# Learning HTML

This note covers the foundational structures of HTML.

Here is an image of the HTML5 logo:
![[html5-logo.png]]

Please check out the sibling article on [[Articles/Introduction to CSS|Introduction to CSS]] for styling options.
```

### Supported Markdown syntax

- **Headers**: Use `# Heading` through `###### Heading`. Since the first `#` is consumed as the page title, body sections should start at `##`. All heading levels map one-to-one to their HTML counterparts (`##` becomes `<h2>`, etc.).
- **Bold and italic**: Use `**bold**` and `*italic*`.
- **Inline code**: Use `` `code` ``.
- **Fenced code blocks**: Wrap in triple backticks. Output is `<pre><code>`.
- **Bullet lists**: Use `- ` prefix, indented to nest.
- **Numbered lists**: Use `1. ` prefix.
- **Blockquotes**: Use `> ` prefix.
- **Wikilinks**: Use `[[Target Note]]` or `[[Target Note|Display Text]]`. The compiler resolves these to relative HTML paths automatically. When no alias is given, the link text is the clean note filename (folder path and `.md` extension stripped).
- **Image transclusions**: Use `![[image.png]]`. The compiler scans the entire vault to locate the file, copies it to the configured output path, and generates a correct relative `<img>` tag.

## 4. Wikilinks and Image Paths

### Wikilinks

Wikilinks reference notes by vault path. The compiler resolves them to relative HTML paths based on the output routing configuration.

```markdown
[[Projects/Active/Project One]]
[[Articles/Learning HTML|HTML Guide]]
```

A link from a note in `articles/` to one in `projects/` automatically generates the correct relative path (e.g. `../../projects/project-one/index.html`).

### Image transclusions

Images can live anywhere in the vault, completely separate from the notes that use them. Reference by filename only:

```markdown
![[html5-logo.png]]
![[css3-badge.png]]
```

The compiler locates the file by scanning the vault recursively, copies it to the configured image destination, and writes the correct relative `src` path in the `<img>` tag.

> [!IMPORTANT]
> All image filenames across the entire vault must be unique. The compiler raises a `BuildError` and halts immediately if two images in different folders share the same name.

## 5. Configuring the Build (`site.json`)

Create a `site.json` file in the root of the repository to control the build pipeline.

```json
{
  "source_vault": "./vault",
  "target_site": "./public",
  "templates": {
    "source_dir": "./templates",
    "mapping": {
      "Articles/": "article.html",
      "default": "layout.html"
    }
  },
  "routes": [
    { "source": "Articles/", "target": "articles/" },
    { "source": "Projects/Active/", "target": "projects/" },
    { "source": "/", "target": "/" }
  ],
  "image_mapping": {
    "global_target": "assets/img",
    "overrides": {
      "Articles/": "articles/img"
    }
  }
}
```

### Key parameters

- `source_vault`: Path to the Obsidian vault directory.
- `target_site`: Path where the compiled site will be written.
- `templates.source_dir`: Directory containing your HTML layout files.
- `templates.mapping`: Maps vault folder prefixes to template files. Use `"default"` as the fallback for all unmatched notes.
- `routes`: Maps vault folder prefixes to output URL paths. A `"source": "/"` catch-all route handles root-level notes like a home page.
- `image_mapping.global_target`: Default output folder for all images.
- `image_mapping.overrides`: Per-folder override destinations (e.g. article images go to `articles/img/` instead of the global `assets/img/`).

## 6. Authoring Layout Templates

Templates are strict XHTML5 files. The engine uses Python's built-in `xml.etree.ElementTree` to parse and inject content, so templates must be well-formed XML.

### Template injection hooks

Two special `<template>` placeholder tags are replaced at compile time:

| Tag | Replaced with |
|---|---|
| `<template id="title">` | The page title (from the note's first `#` heading) |
| `<template id="content">` | The compiled HTML body of the note |

These placeholders can be placed anywhere in the HTML structure.

### Adding headers and footers

Since templates are plain HTML, you add headers, navbars, and footers directly in the template file. The compiler only touches the two `<template>` placeholders and leaves everything else unchanged.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title><template id="title">Default Title</template></title>
</head>
<body>
  <header>
    <nav>
      <a href="/">Home</a>
    </nav>
    <h1><template id="title">Default Title</template></h1>
  </header>
  <main>
    <template id="content"></template>
  </main>
  <footer>
    <p>My Site Footer.</p>
  </footer>
</body>
</html>
```

Notice that `<template id="title">` appears twice: once in `<title>` for the browser tab and once in `<h1>` for the visible page heading. Both are replaced with the same title string.

### Template rules

- All tags must be properly closed (e.g. `<meta charset="UTF-8" />`, not `<meta charset="UTF-8">`).
- All attribute values must be quoted.
- The compiled content body is injected as child nodes of the `<template id="content">` parent element.

### Per-folder templates

Different vault folders can use different templates. For example, article notes can have a sidebar layout while project notes use a minimal layout. This is configured in `templates.mapping` in `site.json`.

## 7. Output Structure

Each note compiles to a clean URL directory containing `index.html`.

```text
public/
├── index.html                          (Home Page.md)
├── assets/img/
│   ├── html5-logo.png
│   └── css3-badge.png
├── articles/
│   ├── img/
│   │   └── header_image.png
│   ├── learning-html/
│   │   └── index.html
│   └── introduction-to-css/
│       └── index.html
└── projects/
    ├── project-one/
    │   └── index.html
    └── project-two/
        └── index.html
```

This structure allows web servers to serve clean extensionless URLs such as `/articles/learning-html/` while also allowing the site to be browsed directly from the filesystem by opening any `index.html`.

## 8. Running the Compiler

Run from the repository root:

```bash
python3 main.py
```

The compiler prints progress to `stdout` and halts with an error message if a build-critical problem is encountered. Review the generated `./public` folder to inspect the compiled pages and copied assets.
