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

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]

# Copy the core agent logic
COPY . .

# Ensure git is globally configured for the AI agent
RUN git config --global user.name "Agentic SDLC" && \
    git config --global user.email "shadman.jamil@gmail.com"

# Expose FastAPI port
EXPOSE 8000

# Run the listener (or your entrypoint)
CMD ["python", "ai-agents-core/jira_listener.py"]