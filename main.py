#!/usr/bin/env python3
"""
Main entry point for the AI Document Pipeline.
Provides both modern Protocol-based architecture and backward compatibility.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.cli_modern import cli

if __name__ == "__main__":
    cli()