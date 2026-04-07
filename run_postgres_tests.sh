#!/bin/bash
# Script to run PostgreSQL migration tests with automatic setup and teardown
# Usage: ./run_postgres_tests.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting PostgreSQL test database...${NC}"
docker compose -f docker-compose.test.yml up -d

# Wait for PostgreSQL to be healthy
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker compose -f docker-compose.test.yml ps | grep -q "(healthy)"; then
        echo -e "${GREEN}PostgreSQL is ready!${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}PostgreSQL failed to become healthy after ${MAX_RETRIES} seconds${NC}"
        docker compose -f docker-compose.test.yml down
        exit 1
    fi
    sleep 1
done

# Run the tests
echo -e "${YELLOW}Running PostgreSQL migration tests...${NC}"
TEST_EXIT_CODE=0
pytest -v tests -n 1 -m requires_postgres --no-cov || TEST_EXIT_CODE=$?

# Tear down the database
echo -e "${YELLOW}Stopping PostgreSQL test database...${NC}"
docker compose -f docker-compose.test.yml down

# Report results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed! ✗${NC}"
    exit $TEST_EXIT_CODE
fi
