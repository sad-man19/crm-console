#!/bin/bash

# Install system dependencies for Playwright Chromium
apt-get update -qq
apt-get install -y -qq libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 libxshmfence1 > /dev/null 2>&1

# Install Playwright Chromium browser
python -m playwright install chromium > /dev/null 2>&1

# Start the Flask app with Gunicorn
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1
