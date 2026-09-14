#!/bin/bash
python -m playwright install > /dev/null 2>&1
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1
