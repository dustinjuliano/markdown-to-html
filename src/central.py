"""Central orchestrator for static site generation

This module scans the source Obsidian vault, calculates permalinks,
resolves wiki links, copies images, and builds the HTML output
"""

import json
import os
import shutil
import re
from os.path import (
  abspath,
  dirname,
  exists,
  isabs,
  join,
  normpath,
  relpath,
)

from src.codegen import generate_html
from src.config import is_safe_path, load_config

class BuildError(Exception):
  """Exception raised for build pipeline errors"""
  pass



def slugify(name: str) -> str:
  """Converts a name to a lowercased slug.

  Args:
      name (`str`): The name to slugify

  Returns:
      `str`: The slugified string
  """
  clean = ""
  for char in name:
    if char.isalnum() == True:
      clean += char.lower()
    elif (char == " ") or (char == "-") or (char == "_"):
      clean += "-"
  while "--" in clean:
    clean = clean.replace("--", "-")
  return clean.strip("-")


def build_site(config_path: str) -> None:
  """Executes the site generation process without filesystem traversals

  Args:
      config_path (`str`): Path to the site.json or config.json file
  """
  print("Loading configuration...")
  config = load_config(config_path)
  src_vault = config["source_vault"]
  tgt_site = config["target_site"]
  if exists(src_vault) == False:
    print(f"Error: Source vault '{src_vault}' does not exist")
    return
  os.makedirs(tgt_site, exist_ok=True)

  # Build md_mappings from export
  md_mappings = {}
  for item in config["export"]:
    md_mappings[item["source"]] = item["target"]

  # Load templates mapping
  templates_config = config["templates"]
  tpl_src = templates_config["source_dir"]
  tpl_mapping = templates_config["mapping"]
  loaded_templates = {}
  print("Loading templates...")
  for key, filename in tpl_mapping.items():
    tpl_path = join(tpl_src, filename)
    if exists(tpl_path) == False:
      print(f"Warning: Template file '{tpl_path}' not found")
      continue
    with open(tpl_path, "r", encoding="utf-8") as tf:
      loaded_templates[key] = tf.read()
  if ("default" in loaded_templates) == False:
    print("Error: Default template not found in mapping")
    return

  copied_images = {}  # maps candidate_tgt to candidate_src

  # Process and compile each export
  for item in config["export"]:
    rel_src = item["source"]
    rel_tgt = item["target"]
    full_src = join(src_vault, rel_src)
    full_tgt = join(tgt_site, rel_tgt)

    if is_safe_path(tgt_site, full_tgt) == False:
      print(f"Security Warning: Skipping unsafe write: {rel_tgt}")
      continue

    if exists(full_src) == False:
      print(f"Warning: Source file '{full_src}' not found")
      continue

    with open(full_src, "r", encoding="utf-8") as f:
      md_content = f.read()

    # Extract first heading as title and remove it from content to prevent duplicate H1
    md_lines = md_content.splitlines()
    first_heading_idx = -1
    extracted_title = None
    for idx, line in enumerate(md_lines):
      stripped = line.strip()
      match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
      if match is not None:
        first_heading_idx = idx
        raw_title = match.group(2).strip()
        # Clean any markdown formatting (e.g. bold, italics, code) from the title
        extracted_title = re.sub(r"\*\*|__|\*|_|`", "", raw_title)
        break

    if first_heading_idx != -1:
      title = extracted_title
      md_lines.pop(first_heading_idx)
      md_content = "\n".join(md_lines)
    else:
      title = os.path.basename(rel_src)[:-3]

    template_content = loaded_templates["default"]
    for prefix, filename in tpl_mapping.items():
      if prefix == "default":
        continue
      clean_prefix = prefix.rstrip("/")
      if rel_src.startswith(clean_prefix + "/") == True:
        if (prefix in loaded_templates) == True:
          template_content = loaded_templates[prefix]
          break

    current_tgt_dir = dirname(rel_tgt)

    def resolve_link(target: str) -> str:
      if target.endswith(".md") == False:
        target_md = target + ".md"
      else:
        target_md = target
      found_rel_tgt = None
      if (target_md in md_mappings) == True:
        found_rel_tgt = md_mappings[target_md]
      else:
        for key, val in md_mappings.items():
          if key.endswith("/" + target_md) == True:
            found_rel_tgt = val
            break
      if found_rel_tgt is not None:
        rel_file = relpath(found_rel_tgt, current_tgt_dir)
        return rel_file.replace("\\", "/")
      print(f"Warning: Link target '{target}' not found")
      return "#"

    def resolve_image(target: str) -> str:
      found_candidates = []
      for media_item in config["media"]:
        media_src = media_item["source"]
        media_tgt = media_item["target"]
        candidate_src = normpath(join(media_src, target)).replace("\\", "/")
        full_image_src = join(src_vault, candidate_src)
        if exists(full_image_src) == True:
          candidate_tgt = normpath(join(media_tgt, target)).replace("\\", "/")
          found_candidates.append((candidate_src, candidate_tgt))

      if len(found_candidates) == 0:
        print(f"Warning: Image asset '{target}' not found")
        return "#"

      # Check for duplicate conflict
      unique_srcs = list(dict.fromkeys([src for src, tgt in found_candidates]))
      if len(unique_srcs) > 1:
        raise BuildError(
          f"Duplicate image filename detected: {unique_srcs[0]} conflicts with {unique_srcs[1]}"
        )

      # Otherwise, use the single resolved candidate
      candidate_src, candidate_tgt = found_candidates[0]
      full_image_src = join(src_vault, candidate_src)
      full_image_tgt = join(tgt_site, candidate_tgt)

      if is_safe_path(tgt_site, full_image_tgt) == False:
        print(f"Security Warning: Skipping unsafe write: {candidate_tgt}")
        return "#"

      if (candidate_tgt in copied_images) == True:
        if copied_images[candidate_tgt] != candidate_src:
          raise BuildError(
            f"Duplicate image filename detected: {candidate_src} conflicts with {copied_images[candidate_tgt]}"
          )
      else:
        os.makedirs(dirname(full_image_tgt), exist_ok=True)
        shutil.copy2(full_image_src, full_image_tgt)
        copied_images[candidate_tgt] = candidate_src
        print(f"Copied image: {candidate_src} -> {candidate_tgt}")

      rel_file = relpath(candidate_tgt, current_tgt_dir)
      return rel_file.replace("\\", "/")

    try:
      html_output = generate_html(
        md_content,
        template_content,
        title,
        resolve_link,
        resolve_image,
      )
    except BuildError:
      raise
    except Exception as e:
      print(f"Error compiling {rel_src}: {str(e)}")
      continue

    os.makedirs(dirname(full_tgt), exist_ok=True)
    with open(full_tgt, "w", encoding="utf-8") as out_f:
      out_f.write(html_output)
    print(f"Compiled page: {rel_src} -> {rel_tgt}")

  print("Build complete!")
