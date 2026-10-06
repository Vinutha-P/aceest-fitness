# ---- Stage 1: Dependencies -------------------------------------------------
# Install into a virtualenv so the final image stays slim and we do not
# rely on Debian's system-packages warning.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---- Stage 2: Runtime ------------------------------------------------------
# Final image contains only the virtualenv and the application code.
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="ACEest Fitness & Gym" \
      org.opencontainers.image.description="Flask gym management API" \
      org.opencontainers.image.version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DATABASE=/data/aceest_fitness.db

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY . .

# Run as a non-root user for improved container security.
RUN useradd --create-home --shell /bin/bash aceest \
    && mkdir -p /data \
    && chown -R aceest:aceest /app /data
USER aceest

VOLUME ["/data"]

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:5000/health').status==200 else 1)"

CMD ["python", "app.py"]