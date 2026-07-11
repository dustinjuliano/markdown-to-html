"""Unit tests for the markdown parsing library

This module validates that markdown block structures and inline formatting
are correctly parsed into XHTML-compliant syntax
"""

import unittest
from src.parse_md import _MAX_BLOCKQUOTE_DEPTH, parse_inline, parse_markdown


class TestParse(unittest.TestCase):
  """Test suite for the custom markdown parser"""

  def setUp(self) -> None:
    """Configures the dummy link and image resolvers"""
    self.link_resolver = lambda t: f"resolved-link/{t}"
    self.image_resolver = lambda t: f"resolved-img/{t}"

  def test_parse_inline_non_string_raises(self) -> None:
    """Verifies that non-string input to parse_inline raises AssertionError"""
    with self.assertRaises(AssertionError):
      parse_inline(42, self.link_resolver, self.image_resolver)

  def test_parse_inline_none_raises(self) -> None:
    """Verifies that None input to parse_inline raises AssertionError"""
    with self.assertRaises(AssertionError):
      parse_inline(None, self.link_resolver, self.image_resolver)

  def test_parse_non_string_raises(self) -> None:
    """Verifies that non-string inputs raise AssertionError"""
    with self.assertRaises(AssertionError):
      parse_markdown(123, self.link_resolver, self.image_resolver)

  def test_parse_headers(self) -> None:
    """Verifies that headers are correctly parsed into XHTML tags"""
    markdown = "# Header 1\n## Header 2\n###### Header 6"
    expected = "<h1>Header 1</h1>\n<h2>Header 2</h2>\n<h6>Header 6</h6>"
    result = parse_markdown(
      markdown, self.link_resolver, self.image_resolver
    )
    self.assertEqual(result, expected)

  def test_parse_bold_italic(self) -> None:
    """Verifies that bold and italic syntax are parsed correctly"""
    markdown = "This is **bold** and this is *italic*"
    expected = "<p>This is <strong>bold</strong> and this is <em>italic</em></p>"
    result = parse_markdown(
      markdown, self.link_resolver, self.image_resolver
    )
    self.assertEqual(result, expected)

  def test_parse_wikilinks(self) -> None:
    """Verifies that Obsidian wikilinks and aliases are parsed correctly"""
    markdown = "Link to [[Folder/Sub/My Page]] or [[Other Page|Alias]]"
    expected = (
      "<p>Link to <a href=\"resolved-link/Folder/Sub/My Page\">My Page</a> "
      "or <a href=\"resolved-link/Other Page\">Alias</a></p>"
    )
    result = parse_markdown(
      markdown, self.link_resolver, self.image_resolver
    )
    self.assertEqual(result, expected)

  def test_parse_images(self) -> None:
    """Verifies that Obsidian image embeds are parsed correctly"""
    markdown = "Image here: ![[photo.png]] and ![[photo.png|My Photo]]"
    expected = (
      "<p>Image here: <img src=\"resolved-img/photo.png\" "
      "alt=\"photo.png\" /> and <img src=\"resolved-img/photo.png\" "
      "alt=\"My Photo\" /></p>"
    )
    result = parse_markdown(
      markdown, self.link_resolver, self.image_resolver
    )
    self.assertEqual(result, expected)

  def test_parse_lists(self) -> None:
    """Verifies that nested and flat lists are parsed correctly"""
    markdown = "- Item 1\n  - Item 1.1\n- Item 2"
    expected = (
      "<ul>\n<li>\nItem 1\n<ul>\n<li>\nItem 1.1\n</li>\n"
      "</ul>\n</li>\n<li>\nItem 2\n</li>\n</ul>"
    )
    result = parse_markdown(
      markdown, self.link_resolver, self.image_resolver
    )
    self.assertEqual(result, expected)

  def test_parse_ordered_lists(self) -> None:
    """Verifies that ordered lists are parsed correctly into ol tags"""
    markdown = "1. Item 1\n2. Item 2"
    expected = (
      "<ol>\n<li>\nItem 1\n</li>\n<li>\nItem 2\n</li>\n</ol>"
    )
    result = parse_markdown(
      markdown, self.link_resolver, self.image_resolver
    )
    self.assertEqual(result, expected)

  def test_parse_blockquotes(self) -> None:
    """Verifies blockquote conversion block parsing"""
    markdown = "> This is a quote"
    expected = "<blockquote>\n<p>This is a quote</p>\n</blockquote>"
    result = parse_markdown(
      markdown, self.link_resolver, self.image_resolver
    )
    self.assertEqual(result, expected)

  def test_parse_fenced_code_blocks(self) -> None:
    """Verifies block code fences conversion with html entity escaping"""
    markdown = "```\ndef hello():\n    return True\n```"
    expected = "<pre><code>def hello():\n    return True</code></pre>"
    result = parse_markdown(
      markdown, self.link_resolver, self.image_resolver
    )
    self.assertEqual(result, expected)

  def test_parse_inline_code(self) -> None:
    """Verifies inline backtick code parsing does not map formatting tags inside"""
    markdown = "Verify `def **test**():` code is not bolded inside backticks"
    expected = (
      "<p>Verify <code>def **test**():</code> code is not bolded inside backticks</p>"
    )
    result = parse_markdown(
      markdown, self.link_resolver, self.image_resolver
    )
    self.assertEqual(result, expected)

  def test_parse_html_escaping(self) -> None:
    """Verifies HTML characters are safely escaped to entities"""
    markdown = "Check symbols: <, >, &"
    expected = "<p>Check symbols: &lt;, &gt;, &amp;</p>"
    result = parse_markdown(
      markdown, self.link_resolver, self.image_resolver
    )
    self.assertEqual(result, expected)

  def test_blockquote_depth_limit_raises(self) -> None:
    """Verifies that excessively nested blockquotes raise AssertionError.

    Constructs a single line prefixed with more `> ` levels than
    `_MAX_BLOCKQUOTE_DEPTH` allows. Each recursive call to
    `parse_markdown` strips one `> ` prefix and increments the depth
    counter, so the guard fires before the Python call stack is exhausted.
    """
    # Build a single line with enough "> " prefixes to exceed the limit
    depth = _MAX_BLOCKQUOTE_DEPTH + 2
    nested = ("> " * depth) + "line"
    with self.assertRaises(AssertionError):
      parse_markdown(nested, self.link_resolver, self.image_resolver)


if __name__ == "__main__":
  unittest.main()
