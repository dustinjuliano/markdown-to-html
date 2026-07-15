"""Main entry point for the static site generator CLI

This module triggers the site build process using the default
configuration file path or a dynamic argument
"""

import os
import sys
from src.central import build_site


def main() -> None:
  """Runs the builder with dynamic config path detection"""
  config_path = "site.json"
  if len(sys.argv) > 1:
    config_path = sys.argv[1]
  elif os.path.exists("config.json") == True:
    config_path = "config.json"
  build_site(config_path)


if __name__ == "__main__":
  main()
