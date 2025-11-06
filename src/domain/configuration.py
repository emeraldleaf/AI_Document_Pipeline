"""
Configuration management module implementing centralized configuration
following the Dependency Inversion Principle.
"""

import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
import json
import logging

from .protocols import ConfigurationProvider, ConfigurationError


@dataclass(frozen=True)
class AppConfiguration:
    """Immutable application configuration."""
    
    # Core directories
    input_directory: Path = field(default_factory=lambda: Path("documents/input"))
    output_directory: Path = field(default_factory=lambda: Path("documents/output"))
    temp_directory: Path = field(default_factory=lambda: Path("documents/temp"))
    
    # Database settings
    database_url: Optional[str] = None
    use_database: bool = False
    
    # Classification categories
    categories: List[str] = field(default_factory=lambda: [
        "invoice", "receipt", "contract", "report", "letter", "form", 
        "presentation", "spreadsheet", "manual", "other"
    ])
    
    # OCR settings
    ocr_language: str = "eng"
    ocr_preprocessing: bool = True
    ocr_min_confidence: float = 60.0
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Processing settings
    max_file_size_mb: int = 50
    max_pages_per_document: int = 100
    parallel_processing: bool = True
    
    @classmethod
    def from_env(cls) -> "AppConfiguration":
        """Create configuration from environment variables."""
        return cls(
            input_directory=Path(os.getenv("DOC_INPUT_DIR", "documents/input")),
            output_directory=Path(os.getenv("DOC_OUTPUT_DIR", "documents/output")),
            temp_directory=Path(os.getenv("DOC_TEMP_DIR", "documents/temp")),
            database_url=os.getenv("DATABASE_URL"),
            use_database=os.getenv("USE_DATABASE", "false").lower() == "true",
            categories=cls._parse_categories_from_env(),
            ocr_language=os.getenv("OCR_LANGUAGE", "eng"),
            ocr_preprocessing=os.getenv("OCR_PREPROCESSING", "true").lower() == "true",
            ocr_min_confidence=float(os.getenv("OCR_MIN_CONFIDENCE", "60.0")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "50")),
            max_pages_per_document=int(os.getenv("MAX_PAGES_PER_DOCUMENT", "100")),
            parallel_processing=os.getenv("PARALLEL_PROCESSING", "true").lower() == "true",
        )
    
    @classmethod
    def from_file(cls, config_path: Path) -> "AppConfiguration":
        """Create configuration from JSON file."""
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            return cls(
                input_directory=Path(data.get("input_directory", "documents/input")),
                output_directory=Path(data.get("output_directory", "documents/output")),
                temp_directory=Path(data.get("temp_directory", "documents/temp")),
                database_url=data.get("database_url"),
                use_database=data.get("use_database", False),
                categories=data.get("categories", cls.__dataclass_fields__["categories"].default_factory()),
                ocr_language=data.get("ocr_language", "eng"),
                ocr_preprocessing=data.get("ocr_preprocessing", True),
                ocr_min_confidence=float(data.get("ocr_min_confidence", 60.0)),
                log_level=data.get("log_level", "INFO"),
                max_file_size_mb=int(data.get("max_file_size_mb", 50)),
                max_pages_per_document=int(data.get("max_pages_per_document", 100)),
                parallel_processing=data.get("parallel_processing", True),
            )
        except (json.JSONDecodeError, ValueError) as e:
            raise ConfigurationError(f"Invalid configuration file: {e}")
    
    @staticmethod
    def _parse_categories_from_env() -> List[str]:
        """Parse categories from environment variable."""
        categories_str = os.getenv("DOC_CATEGORIES")
        if categories_str:
            return [cat.strip() for cat in categories_str.split(",")]
        return [
            "invoice", "receipt", "contract", "report", "letter", "form",
            "presentation", "spreadsheet", "manual", "other"
        ]
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        for directory in [self.input_directory, self.output_directory, self.temp_directory]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if self.use_database and not self.database_url:
            raise ConfigurationError("Database URL required when use_database is True")
        
        if self.ocr_min_confidence < 0 or self.ocr_min_confidence > 100:
            raise ConfigurationError("OCR confidence must be between 0 and 100")
        
        if self.max_file_size_mb <= 0:
            raise ConfigurationError("Max file size must be positive")
        
        if self.max_pages_per_document <= 0:
            raise ConfigurationError("Max pages per document must be positive")
        
        if not self.categories:
            raise ConfigurationError("At least one classification category is required")


class DefaultConfigurationProvider:
    """Default implementation of ConfigurationProvider protocol."""
    
    def __init__(self, config: AppConfiguration):
        self._config = config
        self._config.validate()
        self._config.ensure_directories()
    
    def get_categories(self) -> List[str]:
        """Get list of classification categories."""
        return self._config.categories.copy()
    
    def get_database_url(self) -> Optional[str]:
        """Get database connection URL."""
        return self._config.database_url
    
    def get_output_directory(self) -> Path:
        """Get output directory for organized files."""
        return self._config.output_directory
    
    def use_database(self) -> bool:
        """Check if database storage is enabled."""
        return self._config.use_database
    
    def get_input_directory(self) -> Path:
        """Get input directory for processing."""
        return self._config.input_directory
    
    def get_temp_directory(self) -> Path:
        """Get temporary directory."""
        return self._config.temp_directory
    
    def get_ocr_settings(self) -> dict:
        """Get OCR-related settings."""
        return {
            "language": self._config.ocr_language,
            "preprocessing": self._config.ocr_preprocessing,
            "min_confidence": self._config.ocr_min_confidence,
        }
    
    def get_processing_limits(self) -> dict:
        """Get processing limit settings."""
        return {
            "max_file_size_mb": self._config.max_file_size_mb,
            "max_pages_per_document": self._config.max_pages_per_document,
            "parallel_processing": self._config.parallel_processing,
        }


def setup_logging(config: AppConfiguration) -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format=config.log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ai_document_pipeline.log')
        ]
    )


def load_configuration(config_path: Optional[Path] = None) -> DefaultConfigurationProvider:
    """Load configuration from file or environment variables."""
    if config_path and config_path.exists():
        config = AppConfiguration.from_file(config_path)
    else:
        config = AppConfiguration.from_env()
    
    setup_logging(config)
    return DefaultConfigurationProvider(config)