FROM python:3.12-slim AS builder

WORKDIR /tmp

COPY packages/pprl_service/poetry.lock packages/pprl_service/pyproject.toml /tmp/

RUN python -m pip install poetry==1.8.3 && \
    poetry self add poetry-plugin-export && \
    poetry export -f requirements.txt -o requirements.txt -n

FROM python:3.12-slim

RUN set -ex && adduser --system --no-create-home nonroot

RUN set -ex && \
        apt-get update && \
        apt-get upgrade -y && \
        apt-get autoremove --purge -y && \
        apt-get clean -y && \
        rm -rf /var/lib/apt/lists/*

COPY . /app
COPY --from=builder /tmp/requirements.txt /app/packages/pprl_service/

WORKDIR /app/packages/pprl_service

RUN python -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

EXPOSE 8000/tcp

ENTRYPOINT [ "/usr/local/bin/python", "-m", "uvicorn", "pprl_service.main:app" ]
CMD [ "--host", "0.0.0.0", "--workers", "4" ]

USER nonroot
