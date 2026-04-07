FROM python:3.13

WORKDIR src/

COPY alembic.ini .
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pyproject.toml .

ADD cosmotech/ cosmotech/

RUN pip install .

EXPOSE 8080

ENTRYPOINT [ "uvicorn", "cosmotech.example_api.__main__:app", \
             "--host", "0.0.0.0", \
             "--port=8080", "--proxy-headers" ]
