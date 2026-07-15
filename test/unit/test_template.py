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
    result = render_template(template, title, content, {})
    self.assertEqual(result, expected)

  def test_render_template_malformed(self) -> None:
    """Verifies that a malformed template raises TemplateError"""
    malformed_template = "<html><head><title>Test</title></head><body>"
    with self.assertRaises(TemplateError):
      render_template(malformed_template, "Title", "<p>Content</p>", {})

  def test_render_template_invalid_content_xhtml(self) -> None:
    """Verifies that invalid XHTML block content raises TemplateError"""
    template = (
      '<!DOCTYPE html>\n<html><head>'
      '<title><template id="title">Default</template></title>'
      '</head><body><template id="content"></template></body></html>'
    )
    invalid_content = "<div>unclosed div tag"
    with self.assertRaises(TemplateError):
      render_template(template, "Title", invalid_content, {})

  def test_render_template_with_py_script(self) -> None:
    """Verifies execution of nested python blocks in templates"""
    template = (
      '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
      '  <title><template id="title">Default</template></title>\n'
      '</head>\n<body>\n'
      '  <nav>\n'
      '    <py>\n'
      '      echo(f"<a href=\'{relative_root}index.html\'>Home</a>")\n'
      '    </py>\n'
      '  </nav>\n'
      '  <main><template id="content"></template></main>\n'
      '</body>\n</html>'
    )
    title = "Test Page"
    content = "<p>Content</p>"
    context = {"relative_root": "../"}
    expected = (
      "<!DOCTYPE html>\n<html lang=\"en\">\n  <head>\n"
      "    <title>Test Page</title>\n  </head>\n  <body>\n"
      "    <nav>\n      <a href=\"../index.html\">Home</a>\n    </nav>\n"
      "    <main>\n      <p>Content</p>\n    </main>\n  </body>\n</html>"
    )
    result = render_template(template, title, content, context)
    self.assertEqual(result, expected)

  def test_render_template_py_syntax_error(self) -> None:
    """Verifies that syntax errors in template python raise TemplateError"""
    template = (
      '<html><body>\n'
      '  <py>\n'
      '    invalid python syntax here\n'
      '  </py>\n'
      '</body></html>'
    )
    with self.assertRaises(TemplateError):
      render_template(template, "Title", "", {})

  def test_render_template_py_invalid_xhtml(self) -> None:
    """Verifies that invalid XHTML output from python raises TemplateError"""
    template = (
      '<html><body>\n'
      '  <py>\n'
      '    echo("<div>unclosed div")\n'
      '  </py>\n'
      '</body></html>'
    )
    with self.assertRaises(TemplateError):
      render_template(template, "Title", "", {})


if __name__ == "__main__":
  unittest.main()
