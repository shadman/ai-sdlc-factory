#!/bin/bash

# --- GitHub Authentication ---
if [ -n "$GITHUB_TOKEN" ]; then
    echo $GITHUB_TOKEN | gh auth login --with-token
    # Inject token into all https://github.com clones (no token exposed in logs)
    git config --global url."https://${GIT_USER_NAME}:${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"
fi

# --- Clone product repos if not already present ---
# Checks for .git so it skips on local mounts that already have the repo
BACKEND_DIR="/app/repos/backend"
FRONTEND_DIR="/app/repos/frontend"
BACKEND_REPO="${BACKEND_REPO_URL:-https://github.com/shadman/ai-sdlc-backend.git}"
FRONTEND_REPO="${FRONTEND_REPO_URL:-https://github.com/shadman/ai-sdlc-frontend.git}"

if [ ! -d "$BACKEND_DIR/.git" ]; then
    echo "📦 Backend repo not found — cloning from $BACKEND_REPO ..."
    rm -rf "$BACKEND_DIR"
    git clone "$BACKEND_REPO" "$BACKEND_DIR"
    ls "$BACKEND_DIR"
    git branch
    echo "✅ Backend cloned."
else
    echo "✅ Backend repo already present — skipping clone."
fi

if [ ! -d "$FRONTEND_DIR/.git" ]; then
    echo "📦 Frontend repo not found — cloning from $FRONTEND_REPO ..."
    rm -rf "$FRONTEND_DIR"
    git clone "$FRONTEND_REPO" "$FRONTEND_DIR"
    ls "$FRONTEND_DIR"
    git branch
    echo "✅ Frontend cloned."
else
    echo "✅ Frontend repo already present — skipping clone."
fi

# --- Hand off to CMD / command: override ---
exec "$@"
