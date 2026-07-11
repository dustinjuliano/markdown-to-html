"""Unit tests for the layout templating engine

This module verifies XML parsing, insertion of title and content,
and clean 2-space indented HTML serialization
"""

import unittest
from src.template import TemplateError, render_template


class TestTemplate(unittest.TestCase):
  """Test suite for the XML-based template rendering engine"""

  def test_render_template_success(self) -> None:
    """Verifies that templates insert title and content correctly"""
    template = (
      '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
      '  <title><template id="title">Default</template></title>\n'
      '</head>\n<body>\n'
      '  <main><template id="content"></template></main>\n'
      '</body>\n</html>'
    )
    title = "My Custom Page"
    content = "<p>Inline paragraph content</p>"
    expected = (
      "<!DOCTYPE html>\n<html lang=\"en\">\n  <head>\n"
      "    <title>My Custom Page</title>\n  </head>\n  <body>\n"
      "    <main>\n      <p>Inline paragraph content</p>\n    </main>\n"
      "  </body>\n</html>"
    )
    result = render_template(template, title, content)
    self.assertEqual(result, expected)

  def test_render_template_malformed(self) -> None:
    """Verifies that a malformed template raises TemplateError"""
    malformed_template = "<html><head><title>Test</title></head><body>"
    with self.assertRaises(TemplateError):
      render_template(malformed_template, "Title", "<p>Content</p>")

  def test_render_template_invalid_content_xhtml(self) -> None:
    """Verifies that invalid XHTML block content raises TemplateError"""
    template = (
      '<!DOCTYPE html>\n<html><head>'
      '<title><template id="title">Default</template></title>'
      '</head><body><template id="content"></template></body></html>'
    )
    invalid_content = "<div>unclosed div tag"
    with self.assertRaises(TemplateError):
      render_template(template, "Title", invalid_content)


if __name__ == "__main__":
  unittest.main()
