#!/usr/bin/env python3
"""
FluentAI CLI module main entry point.

This allows the CLI to be run as:
    python -m fluentai.cli.translate_rt
"""

import os
import sys

# Add the parent directory to the path so we can import fluentai modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fluentai.cli.translate_rt import main

if __name__ == "__main__":
    main()
