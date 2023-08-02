#!/bin/sh
docker compose -f docker-compose.dev.yml --profile=kafka down -v
