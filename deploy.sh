#!/bin/bash
ENVS=$(cat user-data.txt | awk -F '[ ]' '{printf "-e " $1 " "}')
docker-compose run $ENVS worker python main.py