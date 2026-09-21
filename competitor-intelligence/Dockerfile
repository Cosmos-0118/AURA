FROM python:3.12-slim

WORKDIR /app
COPY competitor_intelligence ./competitor_intelligence
COPY config ./config
COPY static ./static
COPY pyproject.toml README.md ./

ENV PYTHONUNBUFFERED=1
ENV INTEL_HOST=0.0.0.0
ENV INTEL_PORT=8787
ENV INTEL_DB_PATH=/app/data/intelligence.db

RUN mkdir -p /app/data
EXPOSE 8787
CMD ["python", "-m", "competitor_intelligence"]
