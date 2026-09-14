#!/bin/bash
python -m playwright install chromium-headless-shell > /dev/null 2>&1
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1
