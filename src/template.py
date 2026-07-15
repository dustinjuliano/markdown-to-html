"""XML-based layout template rendering engine

This module uses python's standard xml.etree.ElementTree to parse
strict XHTML templates, replace `<template>` placeholders with HTML,
and serialize the result into HTML5 with clean indentation
"""

import textwrap
import re
from xml.etree.ElementTree import (
  Element,
  fromstring,
  indent,
  tostring,
)


class TemplateError(Exception):
  """Exception raised for template errors"""
  pass


def render_template(
  template_content: str,
  title: str,
  content_html: str,
  context: dict,
) -> str:
  """Renders page content into an XHTML template using ElementTree.

  Args:
      template_content (`str`): The XHTML template content
      title (`str`): The page title to inject
      content_html (`str`): The XHTML parsed body content to inject
      context (`dict`): The execution context dictionary for scripting

  Returns:
      `str`: Clean, indented HTML5 output string

  Raises:
      `TemplateError`: If the template is malformed XML
  """
  def py_block_repl(match):
    code_text = match.group(1)
    # Strip optional CDATA wrappers defensively
    cdata_match = re.match(
      r"^\s*<!\[CDATA\[(.*?)\]\]>\s*$",
      code_text,
      flags=re.DOTALL,
    )
    if cdata_match is not None:
      code_text = cdata_match.group(1)

    clean_code = textwrap.dedent(code_text).strip()
    output_buffer = []

    def echo(text: str) -> None:
      output_buffer.append(text)

    exec_context = dict(context)
    exec_context["echo"] = echo

    try:
      exec(clean_code, exec_context)
    except Exception as e:
      raise TemplateError(
        f"Error executing Python block in template: {str(e)}"
      )
    return "".join(output_buffer)

  try:
    processed_template = re.sub(
      r"<py>(.*?)</py>",
      py_block_repl,
      template_content,
      flags=re.DOTALL,
    )
  except TemplateError:
    raise
  except Exception as e:
    raise TemplateError(
      f"Failed to preprocess template scripts: {str(e)}"
    )

  try:
    root = fromstring(processed_template)
  except Exception as e:
    raise TemplateError(f"Malformed template XML: {str(e)}")

  parent_map = {c: p for p in root.iter() for c in p}

  try:
    content_xml = fromstring(f"<root>{content_html}</root>")
  except Exception as e:
    raise TemplateError(
      f"Markdown output is not valid XHTML: {str(e)}"
    )

  template_nodes = []
  for node in root.iter():
    local_tag = node.tag.split("}")[-1]
    if local_tag == "template":
      template_nodes.append(node)

  for node in template_nodes:
    if (node in parent_map) == False:
      continue
    parent = parent_map[node]
    node_id = node.get("id")

    if node_id == "title":
      parent.text = title
      parent.remove(node)

    elif node_id == "content":
      idx = list(parent).index(node)
      for child in list(content_xml):
        parent.insert(idx, child)
        idx += 1
      parent.remove(node)

  try:
    indent(root, space="  ")
  except Exception as e:
    pass

  try:
    result = tostring(root, encoding="utf-8", method="html")
    html_str = result.decode("utf-8")
    if html_str.strip().startswith("<html") == True:
      return "<!DOCTYPE html>\n" + html_str
    return html_str
  except Exception as e:
    raise TemplateError(f"Serialization failed: {str(e)}")
