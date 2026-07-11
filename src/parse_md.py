"""Custom Markdown to XHTML parser library

This module parses Markdown strings and converts them to XHTML-compliant
HTML blocks for template integration
"""

import os
import re


_MAX_BLOCKQUOTE_DEPTH = 20

def parse_inline(
  text: str, link_resolver, image_resolver
) -> str:
  """Parses inline markdown syntax to HTML.

  Args:
      `text` (`str`): The raw text to process
      `link_resolver` (`callable`): Resolves wikilinks to URLs
      `image_resolver` (`callable`): Resolves image embeds to URLs

  Returns:
      `str`: The inline HTML representation

  Raises:
      `AssertionError`: If `text` is not a `str` instance
  """
  assert isinstance(text, str) == True
  # Escape HTML characters first
  escaped_text = (
    text.replace("&", "&amp;")
    .replace("<", "&lt;")
    .replace(">", "&gt;")
  )

  placeholders = {}
  counter = 0

  def inline_code_repl(match):
    nonlocal counter
    code = match.group(1)
    placeholder = f"___INLINE_CODE_{counter}___"
    placeholders[placeholder] = f"<code>{code}</code>"
    counter += 1
    return placeholder

  # Temporarily isolate inline code
  temp_text = re.sub(r"`([^`\n]+)`", inline_code_repl, escaped_text)

  # Parse Obsidian image embeds: ![[image.png|alt]]
  def image_repl(match):
    target = match.group(1).strip()
    alias = match.group(2)
    alt_text = target
    if alias is not None:
      alt_text = alias.strip()
    resolved = image_resolver(target)
    return f'<img src="{resolved}" alt="{alt_text}" />'

  temp_text = re.sub(
    r"!\[\[([^|\]]+)(?:\|([^\]]+))?\]\]", image_repl, temp_text
  )

  # Parse Obsidian wikilinks: [[target|alias]]
  def link_repl(match):
    target = match.group(1).strip()
    alias = match.group(2)
    if alias is not None and alias.strip() != "":
      link_text = alias.strip()
    else:
      base = os.path.basename(target)
      if base.endswith(".md") == True:
        link_text = base[:-3]
      else:
        link_text = base
    resolved = link_resolver(target)
    return f'<a href="{resolved}">{link_text}</a>'

  temp_text = re.sub(
    r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\]", link_repl, temp_text
  )

  # Parse bold formatting
  temp_text = re.sub(
    r"\*\*(.*?)\*\*", r"<strong>\1</strong>", temp_text
  )

  # Parse italic formatting
  temp_text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", temp_text)

  # Restore inline code segments
  for ph, val in placeholders.items():
    temp_text = temp_text.replace(ph, val)

  return temp_text


def parse_markdown(
  text: str,
  link_resolver,
  image_resolver,
  _depth: int = 0,
) -> str:
  """Converts markdown blocks to XHTML.

  Args:
      `text` (`str`): The raw markdown string
      `link_resolver` (`callable`): Resolves wikilinks to URLs
      `image_resolver` (`callable`): Resolves image embeds to URLs
      `_depth` (`int`): Internal recursion depth counter for
          blockquote nesting; callers must not set this

  Returns:
      `str`: The generated block-level XHTML string

  Raises:
      `AssertionError`: If `text` is not a `str` instance, or if
          `_depth` exceeds `_MAX_BLOCKQUOTE_DEPTH`
  """
  assert isinstance(text, str) == True
  assert _depth <= _MAX_BLOCKQUOTE_DEPTH

  lines = text.splitlines()
  html_blocks = []
  in_code_block = False
  code_block_lines = []
  list_stack = []
  current_block_type = None
  current_block_lines = []

  def close_current_block():
    nonlocal current_block_type, current_block_lines
    if len(current_block_lines) == 0:
      return
    block_content = "\n".join(current_block_lines)
    if current_block_type == "p":
      parsed = parse_inline(
        block_content, link_resolver, image_resolver
      )
      html_blocks.append(f"<p>{parsed}</p>")
    elif current_block_type == "blockquote":
      parsed = parse_markdown(
        block_content,
        link_resolver,
        image_resolver,
        _depth + 1,
      )
      html_blocks.append(
        f"<blockquote>\n{parsed}\n</blockquote>"
      )
    current_block_lines = []
    current_block_type = None

  def close_lists(target_indent=-1):
    while (
      len(list_stack) > 0
      and list_stack[-1][0] > target_indent
    ):
      _, ltype = list_stack.pop()
      html_blocks.append(f"</li>\n</{ltype}>")
    if (
      len(list_stack) > 0
      and list_stack[-1][0] == target_indent
    ):
      html_blocks.append("</li>")

  idx = 0
  while idx < len(lines):
    line = lines[idx]

    # Handle fenced code blocks
    if line.strip().startswith("```"):
      if in_code_block == False:
        close_current_block()
        close_lists()
        in_code_block = True
        code_block_lines = []
      else:
        in_code_block = False
        code_content = "\n".join(code_block_lines)
        escaped_code = (
          code_content.replace("&", "&amp;")
          .replace("<", "&lt;")
          .replace(">", "&gt;")
        )
        html_blocks.append(
          f"<pre><code>{escaped_code}</code></pre>"
        )
      idx += 1
      continue

    if in_code_block == True:
      code_block_lines.append(line)
      idx += 1
      continue

    stripped = line.strip()

    # Empty line resets state
    if stripped == "":
      close_current_block()
      close_lists()
      idx += 1
      continue

    # Handle headers
    if stripped.startswith("#"):
      match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
      if match is not None:
        close_current_block()
        close_lists()
        level = len(match.group(1))
        header_text = match.group(2)
        parsed = parse_inline(
          header_text, link_resolver, image_resolver
        )
        html_blocks.append(f"<h{level}>{parsed}</h{level}>")
        idx += 1
        continue

    # Handle blockquotes
    if stripped.startswith(">"):
      close_lists()
      bq_content = line.lstrip()
      if bq_content.startswith("> "):
        bq_content = bq_content[2:]
      elif bq_content.startswith(">"):
        bq_content = bq_content[1:]
      if current_block_type != "blockquote":
        close_current_block()
        current_block_type = "blockquote"
      current_block_lines.append(bq_content)
      idx += 1
      continue

    # Handle list elements
    indent_match = re.match(r"^(\s*)", line)
    indent = (
      len(indent_match.group(1))
      if indent_match is not None
      else 0
    )
    list_content = line[indent:]
    is_ul = list_content.startswith("- ")
    is_ol = (
      re.match(r"^\d+\.\s+", list_content) is not None
    )

    if is_ul == True or is_ol == True:
      close_current_block()
      if is_ul == True:
        list_type = "ul"
        item_text = list_content[2:]
      else:
        ol_match = re.match(r"^(\d+\.\s+)", list_content)
        list_type = "ol"
        item_text = list_content[len(ol_match.group(1)) :]

      if len(list_stack) == 0:
        list_stack.append((indent, list_type))
        html_blocks.append(f"<{list_type}>\n<li>")
      else:
        top_indent, top_type = list_stack[-1]
        if indent > top_indent:
          list_stack.append((indent, list_type))
          html_blocks.append(f"<{list_type}>\n<li>")
        elif indent < top_indent:
          close_lists(indent)
          if (
            len(list_stack) > 0
            and list_stack[-1][1] != list_type
          ):
            _, old_type = list_stack.pop()
            html_blocks.append(
              f"</{old_type}>\n<{list_type}>\n<li>"
            )
            list_stack.append((indent, list_type))
          else:
            if len(list_stack) == 0:
              list_stack.append((indent, list_type))
              html_blocks.append(f"<{list_type}>\n<li>")
            else:
              html_blocks.append("<li>")
        else:
          if top_type != list_type:
            list_stack.pop()
            html_blocks.append(
              f"</{top_type}>\n<{list_type}>\n<li>"
            )
            list_stack.append((indent, list_type))
          else:
            html_blocks.append("</li>\n<li>")

      parsed_item = parse_inline(
        item_text, link_resolver, image_resolver
      )
      html_blocks.append(parsed_item)
      idx += 1
      continue

    # Handle continuation inside lists
    if len(list_stack) > 0:
      indent_match = re.match(r"^(\s*)", line)
      indent = (
        len(indent_match.group(1))
        if indent_match is not None
        else 0
      )
      if indent > list_stack[-1][0]:
        continuation_text = line[indent:]
        parsed_cont = parse_inline(
          continuation_text, link_resolver, image_resolver
        )
        html_blocks.append("\n" + parsed_cont)
        idx += 1
        continue

    # Standard paragraph line
    close_lists()
    if current_block_type != "p":
      close_current_block()
      current_block_type = "p"
    current_block_lines.append(stripped)
    idx += 1

  close_current_block()
  close_lists()

  assert len(list_stack) == 0
  return "\n".join(html_blocks)
