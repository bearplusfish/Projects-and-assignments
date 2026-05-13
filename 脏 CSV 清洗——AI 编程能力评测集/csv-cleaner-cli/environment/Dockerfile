FROM python:3.11.11-slim-bookworm

LABEL benchmark="csv-cleaner-cli"

RUN pip install --no-cache-dir --upgrade pip

WORKDIR /app

COPY environment/ /app/environment/
COPY solution/ /app/solution/
COPY tests/ /app/tests/

ENTRYPOINT ["/bin/bash"]
