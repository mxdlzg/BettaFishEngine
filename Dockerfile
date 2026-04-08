FROM ghcr.io/astral-sh/uv:latest AS uv

FROM python:3.11-slim

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Prevent Python from writing .pyc files, buffer stdout/stderr, and pin common tooling paths
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/root/.local/bin:${PATH}" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install system dependencies required by scientific Python stack, Playwright, Streamlit, and WeasyPrint PDF
RUN set -euo pipefail; \
    apt-get update; \
    if apt-cache show libgdk-pixbuf-2.0-0 >/dev/null 2>&1; then \
        GDK_PIXBUF_PKG=libgdk-pixbuf-2.0-0; \
    else \
        GDK_PIXBUF_PKG=libgdk-pixbuf2.0-0; \
    fi; \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libgl1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        "${GDK_PIXBUF_PKG}" \
        libffi-dev \
        libcairo2 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libxcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxi6 \
        libxtst6 \
        libnss3 \
        libxrandr2 \
        libxkbcommon0 \
        libasound2 \
        libx11-xcb1 \
        libxshmfence1 \
        libgbm1 \
        ffmpeg; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies first to leverage Docker layer caching
COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt

# Install Playwright browser binaries (system deps already handled above)
RUN python -m playwright install chromium

# Copy application source
COPY . .

# Fail fast if core embedded engine source files are missing
RUN test -f /app/engine_gateway_api.py && \
    test -f /app/QueryEngine/agent.py && \
    test -f /app/QueryEngine/utils/config.py && \
    test -f /app/MediaEngine/agent.py && \
    test -f /app/InsightEngine/agent.py && \
    test -f /app/ReportEngine/agent.py

# Ensure runtime directories exist even if ignored in build context
RUN mkdir -p /ms-playwright logs final_reports insight_engine_streamlit_reports media_engine_streamlit_reports query_engine_streamlit_reports

EXPOSE 8000

# Health check for the API gateway
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command launches the BettaFish FastAPI gateway
CMD ["python", "-m", "uvicorn", "engine_gateway_api:app", "--host", "0.0.0.0", "--port", "8000"]
