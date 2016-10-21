#!/bin/bash
ENVS=$(cat user-data.prod.txt | awk -F '[ ]' '{printf "-e " $1 " "}')
docker-compose run $ENVS worker python main.py