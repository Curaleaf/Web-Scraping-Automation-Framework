#!/usr/bin/env python3
"""Main entry point for the Dispensary Scraper Agent."""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the CLI
from agents.dispensary_scraper.cli import cli

if __name__ == "__main__":
    cli()
