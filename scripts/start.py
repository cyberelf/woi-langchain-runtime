#!/usr/bin/env python3
"""Startup script for LangChain Agent Runtime."""

import sys
import os
from pathlib import Path

# Add the runtime directory to Python path
runtime_dir = Path(__file__).parent.parent
sys.path.insert(0, str(runtime_dir))

from runtime.main import run_server

if __name__ == "__main__":
    print("Starting LangChain Agent Runtime...")
    run_server() 