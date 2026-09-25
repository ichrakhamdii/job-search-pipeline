FROM python:3.11-slim

WORKDIR /srv

# The shared pipeline package lives at the repo root (used by both this backend and the CLI),
# so the build context for this image must be the repo root, not backend/ - see the `docker
# build` command in backend/README.md.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY pipeline/ pipeline/
COPY backend/ backend/

WORKDIR /srv/backend

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
