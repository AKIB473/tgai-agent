#!/usr/bin/env python3
"""
Standalone bot launcher with explicit log file.
Run: python run_bot.py
"""
import sys
import os

# Make sure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "src")

# Redirect all output to log file AND stdout
import logging

LOG_FILE = "bot.log"

# Set up file logging
file_handler = logging.FileHandler(LOG_FILE, mode="a")
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler],
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

print(f"Bot starting... Log: {os.path.abspath(LOG_FILE)}", flush=True)

from tgai_agent.main import cli_entry

cli_entry()
