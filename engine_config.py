"""
Engine configuration loader and resolver for Second Brain Phase I.

Loads engines.json and provides functions to resolve workspace default_engine
to actual provider/model_id/api_key configuration.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global engine configuration
_ENGINE_CONFIG: Optional[Dict[str, Any]] = None


def load_engines_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load engines.json configuration file.
    
    Args:
        config_path: Path to engines.json. If None, looks for engines.json
                     in the project root.
    
    Returns:
        Dictionary with 'default_engine' and 'engines' keys.
    
    Raises:
        FileNotFoundError: If engines.json not found
        json.JSONDecodeError: If JSON is invalid
    """
    global _ENGINE_CONFIG
    
    if config_path is None:
        # Look for engines.json in project root
        project_root = Path(__file__).parent
        config_path = project_root / "engines.json"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"engines.json not found at {config_path}")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Validate structure
    if 'engines' not in config:
        raise ValueError("engines.json must contain 'engines' key")
    
    if 'default_engine' not in config:
        logger.warning("engines.json missing 'default_engine', using first engine")
        config['default_engine'] = list(config['engines'].keys())[0] if config['engines'] else None
    
    _ENGINE_CONFIG = config
    logger.info(f"Loaded engine configuration: {len(config['engines'])} engines, default: {config['default_engine']}")
    
    return config


def get_engine_config(engine_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get engine configuration by key.
    
    Args:
        engine_key: Engine key (e.g., 'chatgpt_4o_full'). If None or 'auto',
                   returns default engine config.
    
    Returns:
        Engine configuration dict with provider, model_id, api_key_env, etc.
        Returns None if engine not found.
    """
    if _ENGINE_CONFIG is None:
        # Try to load if not already loaded
        try:
            load_engines_config()
        except Exception as e:
            logger.error(f"Failed to load engine config: {e}")
            return None
    
    if engine_key is None or engine_key == 'auto':
        engine_key = _ENGINE_CONFIG.get('default_engine')
    
    if engine_key is None:
        logger.warning("No default engine configured")
        return None
    
    engine_config = _ENGINE_CONFIG.get('engines', {}).get(engine_key)
    
    if engine_config is None:
        logger.warning(f"Engine '{engine_key}' not found in configuration")
        return None
    
    return engine_config


def resolve_engine_for_workspace(workspace_default_engine: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Resolve engine configuration for a workspace.
    
    Resolution order:
    1. workspace_default_engine (if set and not 'auto')
    2. Global default_engine from engines.json
    3. None (fallback)
    
    Args:
        workspace_default_engine: Workspace's default_engine setting.
                                  Can be 'auto', an engine key, or None.
    
    Returns:
        Engine configuration dict, or None if resolution fails.
    """
    if workspace_default_engine and workspace_default_engine != 'auto':
        engine_config = get_engine_config(workspace_default_engine)
        if engine_config:
            return engine_config
    
    # Fall back to global default
    return get_engine_config('auto')


def get_provider_and_model(workspace_default_engine: Optional[str] = None) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get provider, model_id, and API key env var name for a workspace.
    
    Args:
        workspace_default_engine: Workspace's default_engine setting.
    
    Returns:
        Tuple of (provider, model_id, api_key_env), or (None, None, None) if not found.
    """
    engine_config = resolve_engine_for_workspace(workspace_default_engine)
    
    if engine_config is None:
        return (None, None, None)
    
    provider = engine_config.get('provider')
    model_id = engine_config.get('model_id')
    api_key_env = engine_config.get('api_key_env')
    
    return (provider, model_id, api_key_env)


def get_api_key_for_engine(engine_config: Dict[str, Any]) -> Optional[str]:
    """
    Get API key from environment for an engine config.
    
    Args:
        engine_config: Engine configuration dict.
    
    Returns:
        API key value from environment, or None if not found.
    """
    api_key_env = engine_config.get('api_key_env')
    if api_key_env:
        return os.getenv(api_key_env)
    return None


def list_available_engines() -> Dict[str, Dict[str, Any]]:
    """
    List all available engines with their labels.
    
    Returns:
        Dictionary mapping engine keys to their configurations.
    """
    if _ENGINE_CONFIG is None:
        try:
            load_engines_config()
        except Exception as e:
            logger.error(f"Failed to load engine config: {e}")
            return {}
    
    engines = _ENGINE_CONFIG.get('engines', {})
    
    # Return simplified view with just label and key
    result = {}
    for key, config in engines.items():
        result[key] = {
            'key': key,
            'label': config.get('label', key),
            'provider': config.get('provider'),
            'model_id': config.get('model_id')
        }
    
    return result


