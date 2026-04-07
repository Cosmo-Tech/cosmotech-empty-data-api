#!/bin/bash
set -euo pipefail

# Generate OpenAPI specification from the API
echo "Generating OpenAPI specification..."
python ./generate_openapi.py

# Generate TypeScript client
echo "Generating TypeScript client..."
docker run --rm \
    -v "$PWD":/local \
    --user "$(id -u):$(id -g)" \
    openapitools/openapi-generator-cli:v7.20.0 generate \
    -i /local/openapi.yaml \
    -c /local/typescript.yml \
    -g typescript-axios \
    -o /local/out/typescript

# Generate Python client with custom templates for PEP 420 support
echo "Generating Python client..."
docker run --rm \
    -v "$PWD":/local \
    --user "$(id -u):$(id -g)" \
    openapitools/openapi-generator-cli:v7.20.0 generate \
    -i /local/openapi.yaml \
    -c /local/python.yml \
    -g python \
    -t /local/templates/python \
    -o /local/out/python

echo "Client generation complete!"
echo "Python client: ./out/python"
echo "TypeScript client: ./out/typescript"
