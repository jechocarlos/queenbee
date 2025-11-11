"""Additional tests for config loader to increase coverage."""

import os
from pathlib import Path

import pytest

from queenbee.config.loader import _substitute_env_vars, load_config


class TestConfigLoaderEdgeCases:
    """Test edge cases and error paths in config loading."""

    def test_load_config_file_not_found(self):
        """Test that loading non-existent config file raises error."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config("/nonexistent/path/config.yaml")

    def test_substitute_env_vars_with_default(self, monkeypatch):
        """Test environment variable substitution with default value."""
        # Unset the variable to ensure default is used
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        
        config = {"key": "${NONEXISTENT_VAR:default_value}"}
        result = _substitute_env_vars(config)
        
        assert result["key"] == "default_value"

    def test_substitute_env_vars_without_default_raises(self, monkeypatch):
        """Test that missing required env var without default raises error."""
        # Unset the variable to ensure it's not available
        monkeypatch.delenv("REQUIRED_VAR", raising=False)
        
        config = {"key": "${REQUIRED_VAR}"}
        
        with pytest.raises(ValueError, match="Environment variable REQUIRED_VAR is required but not set"):
            _substitute_env_vars(config)

    def test_substitute_env_vars_with_list(self, monkeypatch):
        """Test environment variable substitution in list values."""
        monkeypatch.setenv("LIST_VAR", "list_value")
        
        config = ["${LIST_VAR}", "static_value"]
        result = _substitute_env_vars(config)
        
        assert result == ["list_value", "static_value"]

    def test_substitute_env_vars_nested_dict(self, monkeypatch):
        """Test environment variable substitution in nested dictionaries."""
        monkeypatch.setenv("NESTED_VAR", "nested_value")
        
        config = {
            "outer": {
                "inner": "${NESTED_VAR}",
                "static": "value"
            }
        }
        result = _substitute_env_vars(config)
        
        assert result["outer"]["inner"] == "nested_value"
        assert result["outer"]["static"] == "value"

    def test_substitute_env_vars_list_in_dict(self, monkeypatch):
        """Test environment variable substitution in lists within dicts."""
        monkeypatch.setenv("VAR1", "value1")
        monkeypatch.setenv("VAR2", "value2")
        
        config = {
            "items": ["${VAR1}", "${VAR2}", "static"]
        }
        result = _substitute_env_vars(config)
        
        assert result["items"] == ["value1", "value2", "static"]

    def test_substitute_env_vars_non_string_values(self):
        """Test that non-string values are returned unchanged."""
        config = {
            "int_value": 42,
            "float_value": 3.14,
            "bool_value": True,
            "none_value": None
        }
        result = _substitute_env_vars(config)
        
        assert result == config

    def test_substitute_env_vars_string_not_env_var(self):
        """Test that regular strings (not env var format) are unchanged."""
        config = {
            "normal_string": "This is just text",
            "with_dollar": "Price is $5",
            "with_braces": "Object {key: value}"
        }
        result = _substitute_env_vars(config)
        
        assert result == config
