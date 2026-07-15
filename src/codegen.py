"""Markdown-to-HTML code generator

This module acts as a compilation stage that synthesizes parsed
Markdown structures and XHTML templates in-memory
"""

from src.parse_md import parse_markdown
from src.template import render_template


def generate_html(
  markdown_text: str,
  template_content: str,
  title: str,
  link_resolver,
  image_resolver,
  context: dict,
) -> str:
  """Generates final HTML by parsing markdown and inserting into template.

  Args:
      markdown_text (`str`): The raw markdown source text
      template_content (`str`): The raw XHTML template content
      title (`str`): The title of the page
      link_resolver (`callable`): The link resolution helper
      image_resolver (`callable`): The image resolution helper
      context (`dict`): The execution context dictionary for scripting

  Returns:
      `str`: The generated HTML5 string
  """
  content_html = parse_markdown(
    markdown_text, link_resolver, image_resolver
  )
  return render_template(template_content, title, content_html, context)
