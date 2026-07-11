#!/bin/bash
cd "$(dirname "$0")/.." || exit
python3 -m src.main "$@"
