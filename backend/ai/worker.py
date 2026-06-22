#!/usr/bin/env python3
"""AI worker entry point — same as intelligence_worker."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from intelligence_worker import main

if __name__ == "__main__":
    main()
