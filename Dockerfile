# Base image: Ubuntu 22.04 for audio/CUDA compatibility
FROM ubuntu:22.04

# Non-interactive apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system deps: Python, audio, tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    alsa-utils \
    pulseaudio \
    wget \
    curl \
    ffmpeg \
    espeak \
    libasound2-dev \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python defaults (force overwrite if exists)
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Working dir
WORKDIR /app

# Copy and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Ollama server and pull small model (qwen2.5:3b ~2GB, efficient)
RUN curl -fsSL https://ollama.com/install.sh | sh
RUN ollama serve & sleep 5 && ollama pull qwen2.5:3b

# Copy app files
COPY main.py .
COPY jarvis_config.json .

# Expose Ollama port
EXPOSE 11434

# Entry point: Start Ollama in bg, then app (use exec form to fix warning)
CMD ["sh", "-c", "ollama serve & python3 main.py"]