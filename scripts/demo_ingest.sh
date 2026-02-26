#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python -m assistant.interfaces.cli.app db-reset --yes
PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Book a hotel for next week trip with Gibson"
PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Do the Lit review of the TSRGS paper"
PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Buy a birthday present to mike"
PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Discuss the outcome of the TSRGS paper with Paul today"
PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Bring 1 litre of milk when way to home"
PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Ask Paul about his opinion on new research methodology of TSRGS paper"
PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Buy coffee and sugar for home"
echo "--------------------------------"

echo "Cards:"
PYTHONPATH=src python -m assistant.interfaces.cli.app cards-list
echo "--------------------------------"

echo "Envelopes:"
PYTHONPATH=src python -m assistant.interfaces.cli.app envelopes-list
echo "--------------------------------"



