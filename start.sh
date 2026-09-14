#!/bin/bash
python -m playwright install chromium 2>/dev/null
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1
