# Build context: django-liveops/ (one level above example/)
# docker-compose.yml sets: context: .. / dockerfile: example/Dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Install the package (editable-style: copy src into /pkg)
COPY liveops /pkg/liveops
COPY pyproject.toml README.md /pkg/

RUN uv pip install --system \
    "/pkg[celery,redis]" \
    "daphne>=4" \
    "channels[daphne]>=4" \
    "channels-redis>=4"

# Copy example project files
COPY example/ /app/

ENV DJANGO_SETTINGS_MODULE=demo_project.settings \
    PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["bash", "/app/entrypoint.sh"]
