#!/bin/sh
docker compose -f docker-compose.dev.yml -f docker-compose.dev-kafka.yml down -v
