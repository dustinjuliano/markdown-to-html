"""Configuration loader for the static site generator

This module parses and validates the JSON configuration file, ensuring
all paths are safe and mapped correctly
"""

import json
from os.path import abspath, commonpath, exists, join


class ConfigError(Exception):
  """Exception raised for configuration errors"""
  pass


def load_config(config_path: str) -> dict:
  """Loads and validates configuration from a file

  Args:
      config_path (`str`): The path to the JSON configuration file

  Returns:
      `dict`: The validated configuration dictionary

  Raises:
      `ConfigError`: If configuration is invalid
  """
  # Check if config file exists
  if exists(config_path) == False:
    raise ConfigError(f"Config file not found: {config_path}")

  # Read configuration file
  try:
    with open(config_path, "r", encoding="utf-8") as f:
      config = json.load(f)
  except json.JSONDecodeError as e:
    raise ConfigError(f"Malformed JSON in config: {str(e)}")

  # Validate required keys
  required_keys = [
    "source_vault",
    "target_site",
    "templates",
    "routes",
    "image_mapping",
  ]
  for key in required_keys:
    if (key in config) == False:
      raise ConfigError(f"Missing required config key: {key}")

  # Validate types of paths
  if isinstance(config["source_vault"], str) == False:
    raise ConfigError("source_vault must be a string")
  if isinstance(config["target_site"], str) == False:
    raise ConfigError("target_site must be a string")

  # Validate template section
  templates = config["templates"]
  if isinstance(templates, dict) == False:
    raise ConfigError("templates must be a dictionary")
  if ("source_dir" in templates) == False or (
    "mapping" in templates
  ) == False:
    raise ConfigError("templates must have source_dir and mapping")
  if isinstance(templates["source_dir"], str) == False:
    raise ConfigError("templates source_dir must be a string")
  if isinstance(templates["mapping"], dict) == False:
    raise ConfigError("templates mapping must be a dictionary")

  # Validate routes section
  if isinstance(config["routes"], list) == False:
    raise ConfigError("routes must be a list")
  for idx, route in enumerate(config["routes"]):
    if isinstance(route, dict) == False:
      raise ConfigError(f"Route at index {idx} must be a dictionary")
    if ("source" in route) == False or ("target" in route) == False:
      raise ConfigError(
        f"Route at index {idx} must contain source and target"
      )

  # Validate image_mapping section
  img_map = config["image_mapping"]
  if isinstance(img_map, dict) == False:
    raise ConfigError("image_mapping must be a dictionary")
  if ("global_target" in img_map) == False:
    raise ConfigError("image_mapping must contain global_target")
  if isinstance(img_map["global_target"], str) == False:
    raise ConfigError("global_target must be a string")
  if ("overrides" in img_map) == True and isinstance(
    img_map["overrides"], dict
  ) == False:
    raise ConfigError("image overrides must be a dictionary")

  return config


def is_safe_path(base_dir: str, target_path: str) -> bool:
  """Checks if a target path lies within a base directory

  Args:
      base_dir (`str`): The base directory path
      target_path (`str`): The target path to check

  Returns:
      `bool`: True if the path is safe, False otherwise
  """
  abs_base = abspath(base_dir)
  abs_target = abspath(target_path)
  # Ensure target is within base
  try:
    common = commonpath([abs_base, abs_target])
    return (common == abs_base)
  except ValueError:
    return False
