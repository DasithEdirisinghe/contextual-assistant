#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Call Sarah about the Q3 budget next Monday"
PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Idea: New logo should be blue and green"
PYTHONPATH=src python -m assistant.interfaces.cli.app cards-list
PYTHONPATH=src python -m assistant.interfaces.cli.app envelopes-list
