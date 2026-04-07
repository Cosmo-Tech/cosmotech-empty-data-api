# Asset_Investment_Planning_API

Custom Data API for AIP project

## Build image

```
docker build . -t cosmotech/example_api_api:latest
```

## Run image locally

```
docker run -ti --net host -p 8080:8080 cosmotech/example_api_api
```

## Quickstart

```
pip install -e .[test,dev]
uvicorn cosmotech.example_api.__main__:app --host=0.0.0.0 --port=8080
```
Now api is available on [http://localhost:8080/swagger](http://localhost:8080/swagger)

Check content of `config.toml` for database config

Required envvars :
  - `KEYCLOAK_REALM`

## Database Migrations

This project uses Alembic for database schema migrations. The migration system automatically:
- Creates new databases with the latest schema
- Updates existing databases when models change
- Tracks schema versions

See [MIGRATIONS.md](MIGRATIONS.md) for detailed documentation on:
- How migrations work at startup
- Manual migration commands
- Development workflow
- Production deployment
- Troubleshooting

### Quick Start

After installing dependencies, the API will automatically handle migrations on startup. For manual migration management:

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# View migration status
alembic current
```

## Dev setup

run that command once the installation is done
```
pre-commit install
```
now validations will be made before any commit
