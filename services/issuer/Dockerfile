# services/issuer/Dockerfile
FROM python:3.12-slim

RUN pip install aries-cloudagent==0.11.0

WORKDIR /app
COPY issuer/ ./issuer/
COPY config/ ./config/

ENV PYTHONPATH=/app

CMD ["aca-py", "start", "--arg-file", "config/acapy-config.yml"]
