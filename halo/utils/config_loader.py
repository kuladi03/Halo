# halo/utils/config_loader.py
import yaml
import os

DEFAULT_CONFIG_PATH = os.path.join("configs", "settings.yaml")

class Config:
    """Wrapper to allow attribute-style access to config dict."""

    def __init__(self, config_dict):
        self._dict = config_dict
        for key, value in config_dict.items():
            if isinstance(value, dict):
                value = Config(value)
            setattr(self, key, value)

    def __getitem__(self, key):
        return self._dict[key]

    def __repr__(self):
        return str(self._dict)

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Config:
    """Load YAML config and return as Config object."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg_dict = yaml.safe_load(f)
    return Config(cfg_dict)

# Global config instance
config = load_config()
