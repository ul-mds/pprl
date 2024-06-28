FROM python:3.12

COPY . /app

WORKDIR /app/packages/pprl_service

RUN python -m pip install poetry==1.8.3 && \
    poetry install

EXPOSE 8000/tcp

ENTRYPOINT [ "/usr/local/bin/poetry", "run", "uvicorn", "pprl_service.main:app" ]
CMD [ "--host", "0.0.0.0", "--workers", "4" ]
