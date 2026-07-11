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


def get_target_paths(
  src_rel_path: str, config: dict
) -> tuple:
  """Calculates the target directory and permalink path for a file.

  Args:
      src_rel_path (`str`): The relative path from the vault root
      config (`dict`): The loaded configuration dictionary

  Returns:
      `tuple`: A tuple of target directory and target file path
  """
  norm_src = normpath(src_rel_path).replace("\\", "/")
  base_name = os.path.basename(norm_src)
  dir_name = os.path.dirname(norm_src)
  name_lower = base_name.lower()
  is_root = (dir_name == "") or (dir_name == ".")
  is_index = (
    (name_lower == "index.md")
    or (name_lower == "home.md")
    or (name_lower == "home page.md")
  )
  if (is_root == True) and (is_index == True):
    return ("", "index.html")
  matched_route = None
  for route in config["routes"]:
    route_src = route["source"].rstrip("/")
    if (route_src == "") or (route_src == "/"):
      matched_route = route
    elif norm_src.startswith(route_src + "/") == True:
      matched_route = route
      break
  if matched_route is not None:
    route_src = matched_route["source"].rstrip("/")
    route_tgt = matched_route["target"].strip("/")
    if (route_src == "") or (route_src == "/"):
      sub_dir = dir_name
    else:
      sub_dir = dir_name[len(route_src) :].strip("/")
  else:
    route_tgt = ""
    sub_dir = dir_name
  slugified_sub = []
  if len(sub_dir) > 0:
    for seg in sub_dir.split("/"):
      if len(seg) > 0:
        slugified_sub.append(slugify(seg))
  name_without_ext = base_name[:-3]
  slug_name = slugify(name_without_ext)
  tgt_dir_parts = []
  if len(route_tgt) > 0:
    tgt_dir_parts.append(route_tgt)
  tgt_dir_parts.extend(slugified_sub)
  tgt_dir_parts.append(slug_name)
  target_dir = "/".join(tgt_dir_parts)
  target_file = target_dir + "/index.html"
  return (target_dir, target_file)


def get_image_target_path(
  src_rel_path: str, config: dict
) -> str:
  """Calculates the target output path for an image.

  Args:
      src_rel_path (`str`): The relative path from the vault root
      config (`dict`): The loaded configuration dictionary

  Returns:
      `str`: The target file path relative to site root
  """
  norm_src = normpath(src_rel_path).replace("\\", "/")
  base_name = os.path.basename(norm_src)
  dir_name = os.path.dirname(norm_src)
  img_map = config["image_mapping"]
  global_target = img_map["global_target"].strip("/")
  target_dir = global_target
  if "overrides" in img_map:
    for prefix, override_dir in img_map["overrides"].items():
      clean_prefix = prefix.rstrip("/")
      if norm_src.startswith(clean_prefix + "/") == True:
        target_dir = override_dir.strip("/")
        break
  if len(target_dir) > 0:
    return target_dir + "/" + base_name
  return base_name


def build_site(config_path: str) -> None:
  """Executes the site generation process.

  Args:
      config_path (`str`): Path to the site.json config file
  """
  print("Loading configuration...")
  config = load_config(config_path)
  src_vault = config["source_vault"]
  tgt_site = config["target_site"]
  if exists(src_vault) == False:
    print(f"Error: Source vault '{src_vault}' does not exist")
    return
  os.makedirs(tgt_site, exist_ok=True)
  print("Scanning vault...")
  all_vault_files = []
  for root, _, files in os.walk(src_vault):
    for f in files:
      abs_f = join(root, f)
      rel_f = relpath(abs_f, src_vault)
      all_vault_files.append(rel_f)
  md_mappings = {}
  img_mappings = {}
  seen_image_basenames = {}
  for rel_f in all_vault_files:
    if rel_f.endswith(".md") == True:
      _, tgt_file = get_target_paths(rel_f, config)
      md_mappings[rel_f] = tgt_file
    elif (
      rel_f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
      == True
    ):
      basename = os.path.basename(rel_f).lower()
      if (basename in seen_image_basenames) == True:
        first_path = seen_image_basenames[basename]
        raise BuildError(
          f"Duplicate image filename detected: {rel_f} conflicts with {first_path}"
        )
      seen_image_basenames[basename] = rel_f
      tgt_file = get_image_target_path(rel_f, config)
      img_mappings[rel_f] = tgt_file
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
  for rel_src, rel_tgt in img_mappings.items():
    full_src = join(src_vault, rel_src)
    full_tgt = join(tgt_site, rel_tgt)
    if is_safe_path(tgt_site, full_tgt) == False:
      print(f"Security Warning: Skipping unsafe write: {rel_tgt}")
      continue
    os.makedirs(dirname(full_tgt), exist_ok=True)
    shutil.copy2(full_src, full_tgt)
    print(f"Copied image: {rel_src} -> {rel_tgt}")
  for rel_src, rel_tgt in md_mappings.items():
    full_src = join(src_vault, rel_src)
    full_tgt = join(tgt_site, rel_tgt)
    if is_safe_path(tgt_site, full_tgt) == False:
      print(f"Security Warning: Skipping unsafe write: {rel_tgt}")
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
      found_rel_src = None
      if (target_md in md_mappings) == True:
        found_rel_src = target_md
      else:
        for key in md_mappings.keys():
          if key.endswith("/" + target_md) == True:
            found_rel_src = key
            break
      if found_rel_src is not None:
        target_tgt_file = md_mappings[found_rel_src]
        rel_file = relpath(target_tgt_file, current_tgt_dir)
        return rel_file.replace("\\", "/")
      print(f"Warning: Link target '{target}' not found")
      return "#"
    def resolve_image(target: str) -> str:
      found_rel_src = None
      if (target in img_mappings) == True:
        found_rel_src = target
      else:
        for key in img_mappings.keys():
          if key.endswith("/" + target) == True:
            found_rel_src = key
            break
      if found_rel_src is not None:
        target_tgt_file = img_mappings[found_rel_src]
        rel_file = relpath(target_tgt_file, current_tgt_dir)
        return rel_file.replace("\\", "/")
      print(f"Warning: Image asset '{target}' not found")
      return "#"
    try:
      html_output = generate_html(
        md_content,
        template_content,
        title,
        resolve_link,
        resolve_image,
      )
    except Exception as e:
      print(f"Error compiling {rel_src}: {str(e)}")
      continue
    os.makedirs(dirname(full_tgt), exist_ok=True)
    with open(full_tgt, "w", encoding="utf-8") as out_f:
      out_f.write(html_output)
    print(f"Compiled page: {rel_src} -> {rel_tgt}")
  print("Build complete!")
