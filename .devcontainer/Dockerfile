# Development container for AI Document Pipeline
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build essentials
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    # Database clients
    postgresql-client \
    # Network tools
    curl \
    wget \
    netcat \
    # Image processing (for OCR)
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    # PDF processing
    ghostscript \
    # Utilities
    vim \
    nano \
    git \
    jq \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (for docker-in-docker)
RUN apt-get update && apt-get install -y \
    ca-certificates \
    gnupg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# Switch to vscode user (created by base image)
USER vscode

# Install Python development tools
RUN pip install --upgrade pip setuptools wheel

# Install common Python development tools
RUN pip install \
    # Code quality
    black \
    isort \
    flake8 \
    pylint \
    mypy \
    # Testing
    pytest \
    pytest-cov \
    pytest-asyncio \
    pytest-mock \
    # Documentation
    mkdocs \
    mkdocs-material \
    # Utilities
    ipython \
    rich \
    httpie

# Set working directory
WORKDIR /workspace

# Copy requirements and install (if exists)
# Note: This is optional - the postCreateCommand will also install
COPY --chown=vscode:vscode requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Create directories for common tools
RUN mkdir -p \
    /home/vscode/.local/bin \
    /home/vscode/.config \
    /home/vscode/.cache

# Add local bin to PATH
ENV PATH="/home/vscode/.local/bin:${PATH}"

# Set up bash completion and aliases
RUN echo 'alias ll="ls -lah"' >> ~/.bashrc && \
    echo 'alias python=python3' >> ~/.bashrc && \
    echo 'alias pip=pip3' >> ~/.bashrc && \
    echo 'export PS1="\[\e[32m\][\u@\h \W]\$\[\e[0m\] "' >> ~/.bashrc && \
    echo 'cd /workspace' >> ~/.bashrc

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python --version || exit 1

# Default command (will be overridden by docker-compose)
CMD ["/bin/bash"]
