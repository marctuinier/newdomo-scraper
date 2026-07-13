# syntax=docker/dockerfile:1
# Google Chrome for Linux is only published for amd64. On Apple Silicon /
# arm64 hosts this image runs via emulation (Docker Desktop handles this
# automatically); native arm64 servers need qemu binfmt support.
FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

# Base dependencies for headless Chrome
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    apt-transport-https \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 libc6 \
    libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libgcc1 libglib2.0-0 \
    libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 \
    libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 \
    libxrandr2 libxrender1 libxss1 libxtst6 lsb-release xdg-utils unzip \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Install Google Chrome
RUN apt-get update && apt-get install -y wget gnupg --no-install-recommends && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome-archive-keyring.gpg && \
    chmod 644 /usr/share/keyrings/google-chrome-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-archive-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable --no-install-recommends && \
    apt-get purge -y --auto-remove wget gnupg && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /usr/share/keyrings/google-chrome-archive-keyring.gpg /etc/apt/sources.list.d/google-chrome.list && \
    apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY src /app/src

ENV PYTHONUNBUFFERED=1
CMD ["python", "src/main.py"]
