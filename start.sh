#!/bin/bash
python -m playwright install-deps chromium 2>/dev/null
python -m playwright install chromium-headless-shell 2>/dev/null
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1
