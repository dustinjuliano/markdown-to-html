"""Main entry point for the static site generator CLI

This module triggers the site build process using the default
configuration file path
"""

from src.central import build_site


def main() -> None:
  """Runs the builder with the default config path."""
  build_site("site.json")


if __name__ == "__main__":
  main()
