# Use a slim Python image to save RAM/Disk
FROM python:3.11-slim

# Install system dependencies: Git, GitHub CLI (gh), Bandit
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    gnupg \
    && mkdir -p -m 755 /etc/apt/keyrings \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y --no-install-recommends \
    gh \
    bandit \
    && rm -rf /var/lib/apt/lists/*

# Install Node/NPM for Security Scanning (Frontend)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the core agent logic
COPY . .

# Fix execute permission AFTER COPY . . (Windows hosts strip +x bit)
RUN chmod +x entrypoint.sh

# Ensure git is globally configured for the AI agent
RUN git config --global user.name "Agentic SDLC" && \
    git config --global user.email "shadman.jamil@gmail.com"

ENTRYPOINT ["./entrypoint.sh"]

# Expose agents-api port
EXPOSE 9000

# Run the agents-api service
CMD ["bash", "-c", "cd /app/ai-agents-core && uvicorn agents_api:app --host 0.0.0.0 --port 9000"]
