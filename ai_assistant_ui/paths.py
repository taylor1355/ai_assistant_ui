"""Project path configuration."""
import os

# Project root is one directory up from this file
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# Ensure path is absolute
if not os.path.isabs(PROJECT_ROOT):
    PROJECT_ROOT = os.path.abspath(PROJECT_ROOT)
