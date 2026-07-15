"""Integration tests for the static site generator orchestrator

This module exercises the end-to-end building pipeline. It resolves
the mock vault files, applies templates, validates routes, compiles
links, and copies assets using persistent directory targets
"""

import json
import os
import re
import shutil
import unittest
from os.path import exists, isfile, join, normpath
from src.central import BuildError, build_site


class TestCentral(unittest.TestCase):
  """Integration test suite executing the orchestrator pipeline"""

  def setUp(self) -> None:
    """Sets up state by clearing previous outputs if any exist"""
    # Clean previous output directory to ensure test isolation
    if self._testMethodName == "test_integration_build":
      self.output_dir = "./test/mock_output"
      if exists(self.output_dir) == True:
        shutil.rmtree(self.output_dir)
    else:
      self.output_dir = "./test/mock_output_temp"
      if exists(self.output_dir) == True:
        shutil.rmtree(self.output_dir)
      self.addCleanup(lambda: shutil.rmtree(self.output_dir) if exists(self.output_dir) else None)

  def test_integration_build(self) -> None:
    """Runs end-to-end build over mock vault and validates artifacts"""
    # 1. Execute the main build pipeline with the test configuration
    build_site("./test/mock_config.json")

    # 2. Assert homepage generated at root index structure
    home_file = join(self.output_dir, "index.html")
    self.assertEqual(exists(home_file), True)

    with open(home_file, "r", encoding="utf-8") as f:
      home_html = f.read()

    # Verify that the layout template title is set
    self.assertIn("<title>Home Page</title>", home_html)
    # Verify that header element from layout.html is present
    self.assertIn("<h1>Home Page</h1>", home_html)
    # Verify that wikilinks were correctly resolved to relative index paths
    self.assertIn("href=\"articles/learning-html/index.html\"", home_html)
    self.assertIn("href=\"articles/introduction-to-css/index.html\"", home_html)
    self.assertIn("href=\"projects/project-one/index.html\"", home_html)
    self.assertIn("href=\"projects/project-two/index.html\"", home_html)
    # Verify image embed is translated with resolved relative target path
    self.assertIn("<img src=\"articles/img/header_image.png\"", home_html)

    # 3. Assert HTML learning page compiled correctly with custom article template
    html_file = join(self.output_dir, "articles/learning-html/index.html")
    self.assertEqual(exists(html_file), True)

    with open(html_file, "r", encoding="utf-8") as f:
      html_content = f.read()

    # Verify that it uses the article template header containing the title
    self.assertIn("<h1>Learning HTML</h1>", html_content)
    # Verify image transclusion resolves to the shared assets path
    self.assertIn("<img src=\"../../assets/img/html5-logo.png\"", html_content)
    # Verify cross link with alias resolves to sibling folder
    self.assertIn("href=\"../introduction-to-css/index.html\"", html_content)

    # 4. Assert CSS intro page compiled correctly
    css_file = join(self.output_dir, "articles/introduction-to-css/index.html")
    self.assertEqual(exists(css_file), True)

    with open(css_file, "r", encoding="utf-8") as f:
      css_content = f.read()

    # Verify image transclusion resolves to the shared assets path
    self.assertIn("<img src=\"../../assets/img/css3-badge.png\"", css_content)
    # Verify cross link without alias resolves to sibling folder
    self.assertIn("href=\"../learning-html/index.html\"", css_content)
    # Verify link with alias out to Projects resolves correctly
    self.assertIn("href=\"../../projects/project-one/index.html\"", css_content)

    # 5. Assert Project Two page compiled correctly
    two_file = join(self.output_dir, "projects/project-two/index.html")
    self.assertEqual(exists(two_file), True)

    with open(two_file, "r", encoding="utf-8") as f:
      two_content = f.read()

    # Verify that it uses the default base template header containing the title
    self.assertIn("<h1>Project Two</h1>", two_content)
    # Verify relative folder link without alias
    self.assertIn("href=\"../project-one/index.html\"", two_content)
    # Verify link out to Articles/ with alias
    self.assertIn("href=\"../../articles/learning-html/index.html\"", two_content)

    # 6. Assert asset files were correctly copied to target destinations
    self.assertEqual(exists(join(self.output_dir, "articles/img/header_image.png")), True)
    self.assertEqual(exists(join(self.output_dir, "assets/img/html5-logo.png")), True)
    self.assertEqual(exists(join(self.output_dir, "assets/img/css3-badge.png")), True)

    # 7. Verify all relative links and image sources in compiled site exist
    self.assert_no_broken_links()

  def assert_no_broken_links(self) -> None:
    """Verifies that all relative links and image sources in compiled HTML exist on disk"""
    # Walk the output directory
    for root, _, files in os.walk(self.output_dir):
      for f in files:
        if f.endswith(".html") == True:
          html_path = join(root, f)
          with open(html_path, "r", encoding="utf-8") as file_obj:
            content = file_obj.read()
          # Find all href links
          hrefs = re.findall(r'href="([^"]+)"', content)
          # Find all src image links
          srcs = re.findall(r'src="([^"]+)"', content)
          for target in hrefs + srcs:
            # Skip external links or anchor links
            if (
              target.startswith("http://") == True
              or target.startswith("https://") == True
              or target.startswith("#") == True
            ):
              continue
            # Resolve the path relative to the current HTML file
            target_abs = normpath(join(root, target))
            self.assertTrue(
              exists(target_abs),
              msg=f"Broken link detected in {html_path}: '{target}' resolved to non-existent '{target_abs}'"
            )
            self.assertTrue(
              isfile(target_abs),
              msg=f"Link points to a directory instead of a file in {html_path}: '{target}'"
            )

  def test_duplicate_image_error(self) -> None:
    """Validates that duplicate image filenames raise a BuildError"""
    dup_file = "./test/mock_vault/header_image.png"
    # Copy an image file to create a duplicate name in the vault
    shutil.copy2(
      "./test/mock_vault/Articles/header_image.png",
      dup_file
    )
    # We need to map media so that both files are scanned as potential conflicts
    temp_cfg = "./test/temp_dup_config.json"
    cfg_data = {
      "source_vault": "./test/mock_vault",
      "target_site": self.output_dir,
      "templates": {
        "source_dir": "./test/mock_templates",
        "mapping": {
          "default": "layout.html"
        }
      },
      "export": [
        {"source": "Home Page.md", "target": "index.html"}
      ],
      "media": [
        {"source": "Articles/", "target": "assets/img/"},
        {"source": "", "target": "assets/img/"}
      ]
    }
    with open(temp_cfg, "w", encoding="utf-8") as f:
      json.dump(cfg_data, f)
    self.addCleanup(lambda: os.remove(temp_cfg) if exists(temp_cfg) else None)
    try:
      with self.assertRaises(BuildError):
        build_site(temp_cfg)
    finally:
      if exists(dup_file) == True:
        os.remove(dup_file)

  def test_nonexistent_source_vault(self) -> None:
    """Checks grace completion when source_vault does not exist"""
    temp_cfg = "./test/temp_bad_vault_config.json"
    cfg_data = {
      "source_vault": "./test/nonexistent_vault_dir_123",
      "target_site": self.output_dir,
      "templates": {
        "source_dir": "./test/mock_templates",
        "mapping": {
          "default": "layout.html"
        }
      },
      "export": [],
      "media": []
    }
    with open(temp_cfg, "w", encoding="utf-8") as f:
      json.dump(cfg_data, f)
    self.addCleanup(lambda: os.remove(temp_cfg) if exists(temp_cfg) else None)
    build_site(temp_cfg)

  def test_missing_default_template_mapping(self) -> None:
    """Checks grace completion when default template is missing in configuration"""
    temp_cfg = "./test/temp_no_default_tpl.json"
    cfg_data = {
      "source_vault": "./test/mock_vault",
      "target_site": self.output_dir,
      "templates": {
        "source_dir": "./test/mock_templates",
        "mapping": {
          "Articles/": "articles_layout.html"
        }
      },
      "export": [],
      "media": []
    }
    with open(temp_cfg, "w", encoding="utf-8") as f:
      json.dump(cfg_data, f)
    self.addCleanup(lambda: os.remove(temp_cfg) if exists(temp_cfg) else None)
    build_site(temp_cfg)

  def test_missing_template_file_warning(self) -> None:
    """Checks grace completion when template file is missing on disk"""
    temp_cfg = "./test/temp_missing_tpl_file.json"
    cfg_data = {
      "source_vault": "./test/mock_vault",
      "target_site": self.output_dir,
      "templates": {
        "source_dir": "./test/mock_templates",
        "mapping": {
          "default": "nonexistent_layout_file.html"
        }
      },
      "export": [],
      "media": []
    }
    with open(temp_cfg, "w", encoding="utf-8") as f:
      json.dump(cfg_data, f)
    self.addCleanup(lambda: os.remove(temp_cfg) if exists(temp_cfg) else None)
    build_site(temp_cfg)

  def test_unsafe_path_write_skipped(self) -> None:
    """Checks that unsafe target paths are skipped during building"""
    temp_cfg = "./test/temp_unsafe_route.json"
    cfg_data = {
      "source_vault": "./test/mock_vault",
      "target_site": self.output_dir,
      "templates": {
        "source_dir": "./test/mock_templates",
        "mapping": {
          "default": "layout.html"
        }
      },
      "export": [
        {"source": "Home Page.md", "target": "../unsafe_dir/index.html"}
      ],
      "media": [
        {"source": "Articles/", "target": "../unsafe_img/"}
      ]
    }
    with open(temp_cfg, "w", encoding="utf-8") as f:
      json.dump(cfg_data, f)
    self.addCleanup(lambda: os.remove(temp_cfg) if exists(temp_cfg) else None)
    build_site(temp_cfg)
    unsafe_out = "./test/unsafe_dir"
    unsafe_img = "./test/unsafe_img"
    self.assertEqual(exists(unsafe_out), False)
    self.assertEqual(exists(unsafe_img), False)

  def _build_with_mock_config(self, extra_export=None) -> str:
    """Builds the mock vault into self.output_dir using a temp config

    Writes a temporary `site.json` that mirrors `mock_config.json` but
    targets `self.output_dir`, runs the build, registers cleanup, and
    returns the path to the temp config file
    """
    export = extra_export
    if export is None:
      export = [
        {"source": "Home Page.md", "target": "index.html"},
        {"source": "Articles/Learning HTML.md", "target": "articles/learning-html/index.html"},
        {"source": "Articles/Introduction to CSS.md", "target": "articles/introduction-to-css/index.html"},
        {"source": "Articles/No Heading Note.md", "target": "articles/no-heading-note/index.html"},
        {"source": "Projects/Active/Project One.md", "target": "projects/project-one/index.html"},
        {"source": "Projects/Active/Project Two.md", "target": "projects/project-two/index.html"}
      ]
    temp_cfg = "./test/temp_mock_cfg_helper.json"
    cfg_data = {
      "source_vault": "./test/mock_vault",
      "target_site": self.output_dir,
      "templates": {
        "source_dir": "./test/mock_templates",
        "mapping": {
          "Articles/": "articles_layout.html",
          "default": "layout.html"
        }
      },
      "export": export,
      "media": [
        {"source": "Articles/", "target": "articles/img/"},
        {"source": "attachments/", "target": "assets/img/"},
        {"source": "attachments/deep/nested/", "target": "assets/img/"}
      ]
    }
    with open(temp_cfg, "w", encoding="utf-8") as f:
      json.dump(cfg_data, f)
    self.addCleanup(
      lambda: os.remove(temp_cfg) if exists(temp_cfg) else None
    )
    build_site(temp_cfg)
    return temp_cfg

  def test_title_extracted_from_first_heading(self) -> None:
    """Verifies that the page title and H1 are derived from the note's first heading

    Ensures the compiler strips the first `#` heading from the body and
    injects it as both the `<title>` and the `<h1>` via the template hook,
    with no duplicate H1 appearing in the `<main>` content block
    """
    self._build_with_mock_config()
    html_file = join(self.output_dir, "articles/learning-html/index.html")
    self.assertEqual(exists(html_file), True)
    with open(html_file, "r", encoding="utf-8") as f:
      content = f.read()
    # Title tag must use the extracted heading
    self.assertIn("<title>Learning HTML</title>", content)
    # H1 in header must use the extracted heading
    self.assertIn("<h1>Learning HTML</h1>", content)
    # The first heading must NOT appear as a second H1 inside <main>
    h1_count = len(re.findall(r"<h1>", content))
    self.assertEqual(h1_count, 1)

  def test_title_fallback_to_filename(self) -> None:
    """Verifies that a note with no heading falls back to filename as title

    The `No Heading Note.md` vault file contains no `#` heading. The
    compiler must use the basename of the source file (without extension)
    as the page title and inject it into the template `<h1>`
    """
    self._build_with_mock_config()
    fallback_file = join(
      self.output_dir, "articles/no-heading-note/index.html"
    )
    self.assertEqual(exists(fallback_file), True)
    with open(fallback_file, "r", encoding="utf-8") as f:
      content = f.read()
    self.assertIn("<title>No Heading Note</title>", content)
    self.assertIn("<h1>No Heading Note</h1>", content)

  def test_dual_title_hook_in_template(self) -> None:
    """Verifies that the title hook is injected in all positions it appears

    The mock layout templates place `<template id="title">` inside both
    `<title>` and `<h1>`. Both must be replaced with the same title string
    """
    self._build_with_mock_config()
    home_file = join(self.output_dir, "index.html")
    self.assertEqual(exists(home_file), True)
    with open(home_file, "r", encoding="utf-8") as f:
      content = f.read()
    self.assertIn("<title>Home Page</title>", content)
    self.assertIn("<h1>Home Page</h1>", content)

  def test_deeply_nested_image_resolved(self) -> None:
    """Verifies that images in deeply nested vault folders are resolved correctly

    The `deep-image.png` asset lives in
    `attachments/deep/nested/deep-image.png`, far from the note in
    `Articles/` that references it. The compiler must scan media mapping folders,
    find the file, copy it to `assets/img/`, and write the correct
    relative `src` path in the compiled HTML
    """
    self._build_with_mock_config()
    html_file = join(self.output_dir, "articles/learning-html/index.html")
    self.assertEqual(exists(html_file), True)
    with open(html_file, "r", encoding="utf-8") as f:
      content = f.read()
    # Image must be copied to the global assets folder
    copied_img = join(self.output_dir, "assets/img/deep-image.png")
    self.assertEqual(exists(copied_img), True)
    # The compiled HTML must reference it via a correct relative path
    self.assertIn(
      "<img src=\"../../assets/img/deep-image.png\"", content
    )

  def test_unexported_notes_are_not_compiled(self) -> None:
    """Verifies that only notes listed in the export configuration are compiled"""
    # Compile only a subset of notes (excluding Projects)
    self._build_with_mock_config(
      extra_export=[
        {"source": "Home Page.md", "target": "index.html"},
        {"source": "Articles/Learning HTML.md", "target": "articles/learning-html/index.html"}
      ]
    )
    # Exports must exist
    self.assertEqual(exists(join(self.output_dir, "index.html")), True)
    self.assertEqual(exists(join(self.output_dir, "articles/learning-html/index.html")), True)
    # Unexported project notes must not exist
    self.assertEqual(exists(join(self.output_dir, "projects/project-one/index.html")), False)
    self.assertEqual(exists(join(self.output_dir, "projects/project-two/index.html")), False)

  def test_my_first_article_content_correct(self) -> None:
    """Verifies that My First Article compiles with all expected body content

    Exercises nested lists, ordered lists, fenced code blocks, bold, and
    italic in the integration pipeline to catch regressions in the compile
    loop that unit parser tests would not surface
    """
    # Let's add My First Article to the export
    self._build_with_mock_config(
      extra_export=[
        {"source": "Articles/My First Article.md", "target": "articles/my-first-article/index.html"}
      ]
    )
    article_file = join(
      self.output_dir, "articles/my-first-article/index.html"
    )
    self.assertEqual(exists(article_file), True)
    with open(article_file, "r", encoding="utf-8") as f:
      content = f.read()
    self.assertIn("<title>My First Article</title>", content)
    self.assertIn("<h1>My First Article</h1>", content)
    self.assertIn("<h2>Some Section</h2>", content)
    self.assertIn("<ul>", content)
    self.assertIn("<ol>", content)
    self.assertIn("<pre>", content)
    self.assertIn("<code>def hello():", content)
    self.assertIn("<strong>bold</strong>", content)
    self.assertIn("<em>italic</em>", content)



if __name__ == "__main__":
  unittest.main()
