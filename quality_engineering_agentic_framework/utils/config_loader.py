"""
Configuration Loader Module

This module provides functionality for loading and validating configuration.
"""

import os
import yaml
from typing import Dict, Any, Optional

from quality_engineering_agentic_framework.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """Configuration loader for the framework."""
    
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dictionary containing configuration
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            yaml.YAMLError: If the configuration file is not valid YAML
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                logger.info(f"Loaded configuration from {config_path}")
                return config
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {str(e)}")
            raise
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> None:
        """
        Validate the configuration.
        
        Args:
            config: Dictionary containing configuration
            
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for required sections
        required_sections = ["llm", "agents"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate LLM configuration
        llm_config = config.get("llm", {})
        if not llm_config.get("provider"):
            raise ValueError("LLM provider must be specified in configuration")
        
        # Validate agent configurations
        agents_config = config.get("agents", {})
        required_agents = ["test_case_generation", "test_script_generator", "test_data_generator"]
        for agent in required_agents:
            if agent not in agents_config:
                raise ValueError(f"Missing configuration for required agent: {agent}")
        
        logger.info("Configuration validation successful")
    
    @staticmethod
    def get_default_config_path() -> str:
        """
        Get the default configuration file path.
        
        Returns:
            Default configuration file path
        """
        # Get the directory where the package is installed
        package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(os.path.dirname(package_dir), "config", "config.yaml")
    
    @staticmethod
    def load_and_validate_config(config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load and validate configuration.
        
        Args:
            config_path: Path to the configuration file, or None to use default
            
        Returns:
            Dictionary containing validated configuration
        """
        if not config_path:
            config_path = ConfigLoader.get_default_config_path()
        
        config = ConfigLoader.load_config(config_path)
        ConfigLoader.validate_config(config)
        return config