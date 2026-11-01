# Lightweight AI inference service for SmartCampus complaint triage.
# CPU-only, no GPU dependencies.
FROM python:3.13-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.13-slim-bookworm AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd --system ai && useradd --system --ingroup ai --home /home/ai ai

# Copy installed packages from builder
COPY --from=builder /root/.local /home/ai/.local
ENV PATH="/home/ai/.local/bin:$PATH"

# Copy application code
COPY ai_triage/ ./ai_triage/
COPY pyproject.toml .

# Verify artifacts exist at runtime
RUN test -f ai_triage/artifacts/category_model.joblib && \
    test -f ai_triage/artifacts/priority_model.joblib && \
    echo "Model artifacts present" || (echo "ERROR: Model artifacts missing. Run training first." && exit 1)

# Switch to non-root user
USER ai

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start server
CMD ["uvicorn", "ai_triage.serve:app", "--host", "0.0.0.0", "--port", "8000"]
