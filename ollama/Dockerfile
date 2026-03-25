FROM ollama/ollama

# Model to pull on first start — override via OLLAMA_MODEL env var
ENV OLLAMA_MODEL=deepseek-coder-v2:lite

# curl is needed by init.sh to health-check the server
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY init.sh /init.sh
# Strip Windows CRLF line endings and set execute permission
RUN sed -i 's/\r//' /init.sh && chmod +x /init.sh

EXPOSE 11434

ENTRYPOINT ["/init.sh"]
