FROM python:3.12-alpine AS builder

WORKDIR /tmp

COPY packages/pprl_service/poetry.lock packages/pprl_service/pyproject.toml /tmp/

RUN python -m pip install poetry==1.8.3 && \
    poetry self add poetry-plugin-export && \
    poetry export -f requirements.txt -o requirements.txt -n

FROM python:3.12-alpine

# RUN set -ex && adduser --system --no-create-home nonroot
RUN set -ex && \
        addgroup -S nonroot && \
        adduser -S nonroot -G nonroot

COPY . /app
COPY --from=builder /tmp/requirements.txt /app/packages/pprl_service/

WORKDIR /app/packages/pprl_service

RUN python -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

EXPOSE 8000/tcp

ENTRYPOINT [ "/usr/local/bin/python", "-m", "uvicorn", "pprl_service.main:app" ]
CMD [ "--host", "0.0.0.0", "--workers", "4" ]

HEALTHCHECK CMD [ "/usr/local/bin/python", "/app/packages/pprl_service/pprl_service/healthcheck.py" ]

USER nonroot
