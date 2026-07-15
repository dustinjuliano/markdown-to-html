"""Unit tests for the configuration module

This module verifies JSON validation, config schema checks, and path safety rules
"""

import json
import os
import unittest
from src.config import ConfigError, is_safe_path, load_config


class TestConfig(unittest.TestCase):
  """Test suite for configuration validation and path safety"""

  def setUp(self) -> None:
    """Sets up temporary test configuration paths"""
    self.temp_config_path = "./test/temp_test_config.json"

  def tearDown(self) -> None:
    """Cleans up temporary config files"""
    if os.path.exists(self.temp_config_path) == True:
      os.remove(self.temp_config_path)

  def write_temp_config(self, data: dict) -> None:
    """Helper to write configuration dictionary to temp file"""
    with open(self.temp_config_path, "w", encoding="utf-8") as f:
      json.dump(data, f)

  def test_is_safe_path_valid(self) -> None:
    """Verifies that is_safe_path returns True for descendant paths"""
    self.assertEqual(is_safe_path("/tmp", "/tmp/nested/file"), True)

  def test_is_safe_path_invalid(self) -> None:
    """Verifies that is_safe_path returns False for traversal paths"""
    self.assertEqual(is_safe_path("/tmp", "/tmp/../etc/passwd"), False)

  def test_is_safe_path_unrelated_exception(self) -> None:
    """Verifies is_safe_path returns False if ValueError is raised"""
    self.assertEqual(is_safe_path("", "/tmp"), False)

  def test_load_config_not_found(self) -> None:
    """Verifies load_config raises ConfigError if file does not exist"""
    with self.assertRaises(ConfigError):
      load_config("./nonexistent_config_file.json")

  def test_load_config_malformed_json(self) -> None:
    """Verifies load_config raises ConfigError for malformed JSON syntax"""
    with open(self.temp_config_path, "w", encoding="utf-8") as f:
      f.write("{invalid json}")
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

  def test_load_config_success(self) -> None:
    """Verifies load_config successfully parses a fully valid schema"""
    valid_data = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {
        "source_dir": "./templates",
        "mapping": {
          "default": "layout.html"
        }
      },
      "export": [
        {"source": "Home.md", "target": "index.html"}
      ],
      "media": [
        {"source": "attachments/", "target": "assets/img/"}
      ]
    }
    self.write_temp_config(valid_data)
    cfg = load_config(self.temp_config_path)
    self.assertEqual(cfg["source_vault"], "./vault")

  def test_load_config_missing_required_keys(self) -> None:
    """Verifies ConfigError is raised when required keys are missing"""
    keys = ["source_vault", "target_site", "templates", "export", "media"]
    for missing_key in keys:
      valid_data = {
        "source_vault": "./vault",
        "target_site": "./public",
        "templates": {
          "source_dir": "./templates",
          "mapping": {
            "default": "layout.html"
          }
        },
        "export": [
          {"source": "Home.md", "target": "index.html"}
        ],
        "media": [
          {"source": "attachments/", "target": "assets/img/"}
        ]
      }
      del valid_data[missing_key]
      self.write_temp_config(valid_data)
      with self.assertRaises(ConfigError):
        load_config(self.temp_config_path)

  def test_load_config_invalid_types(self) -> None:
    """Verifies ConfigError is raised when paths are not string types"""
    bad_data_1 = {
      "source_vault": 123,
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": [],
      "media": []
    }
    self.write_temp_config(bad_data_1)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    bad_data_2 = {
      "source_vault": "./vault",
      "target_site": True,
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": [],
      "media": []
    }
    self.write_temp_config(bad_data_2)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

  def test_load_config_invalid_templates(self) -> None:
    """Verifies validations for templates mappings and types"""
    # templates must be a dict
    bad_data_1 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": "layout.html",
      "export": [],
      "media": []
    }
    self.write_temp_config(bad_data_1)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # templates must contain source_dir and mapping
    bad_data_2 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates"},
      "export": [],
      "media": []
    }
    self.write_temp_config(bad_data_2)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # templates source_dir must be string
    bad_data_3 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": 123, "mapping": {"default": "layout.html"}},
      "export": [],
      "media": []
    }
    self.write_temp_config(bad_data_3)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # templates mapping must be dict
    bad_data_4 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": []},
      "export": [],
      "media": []
    }
    self.write_temp_config(bad_data_4)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

  def test_load_config_invalid_export(self) -> None:
    """Verifies validations for export configurations"""
    # export must be list
    bad_data_1 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": {},
      "media": []
    }
    self.write_temp_config(bad_data_1)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # export elements must be dicts
    bad_data_2 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": ["Home.md -> index.html"],
      "media": []
    }
    self.write_temp_config(bad_data_2)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # export dict must have source and target
    bad_data_3 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": [{"source": "Home.md"}],
      "media": []
    }
    self.write_temp_config(bad_data_3)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # export source must be string
    bad_data_4 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": [{"source": 123, "target": "index.html"}],
      "media": []
    }
    self.write_temp_config(bad_data_4)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # export target must be string
    bad_data_5 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": [{"source": "Home.md", "target": True}],
      "media": []
    }
    self.write_temp_config(bad_data_5)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

  def test_load_config_invalid_media(self) -> None:
    """Verifies validation of media directory configurations"""
    # media must be list
    bad_data_1 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": [],
      "media": {}
    }
    self.write_temp_config(bad_data_1)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # media elements must be dicts
    bad_data_2 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": [],
      "media": ["attachments/ -> assets/img/"]
    }
    self.write_temp_config(bad_data_2)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # media element must contain source and target
    bad_data_3 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": [],
      "media": [{"source": "attachments/"}]
    }
    self.write_temp_config(bad_data_3)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # media source must be string
    bad_data_4 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": [],
      "media": [{"source": 123, "target": "assets/img/"}]
    }
    self.write_temp_config(bad_data_4)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)

    # media target must be string
    bad_data_5 = {
      "source_vault": "./vault",
      "target_site": "./public",
      "templates": {"source_dir": "./templates", "mapping": {"default": "layout.html"}},
      "export": [],
      "media": [{"source": "attachments/", "target": False}]
    }
    self.write_temp_config(bad_data_5)
    with self.assertRaises(ConfigError):
      load_config(self.temp_config_path)


if __name__ == "__main__":
  unittest.main()
