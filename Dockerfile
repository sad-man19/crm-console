# Official Playwright image: Python + Chromium + all OS-level dependencies
# pre-installed and version-matched. This is what avoids the
# "executable doesn't exist" error you were hitting on the native runtime.
#
# IMPORTANT: the tag version (v1.63.0) must match the playwright version
# pinned in requirements.txt, or Playwright won't find the browser.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

WORKDIR /app

# Install Python deps first so Docker can cache this layer
# (rebuilds are much faster when you only change app code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the app
COPY . .

ENV PYTHONUNBUFFERED=1

# Render assigns the real port via the $PORT env var at runtime.
# Shell form (not exec/array form) is required so $PORT actually expands.
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1
