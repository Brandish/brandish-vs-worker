# brandish-vs-worker

The video statistics worker for the **Brandish Platform.** It's main purpose is to synchronously fetch information from YouTube associated with the items in the DB through their `external_id` parameters. This cycles are run each `LOADER_WAIT_TIME` seconds and they can be setup with through environment variables. The default value is 1800 seconds.

## Tools used

All these tools are defined in the `requirements.txt` file and are installed when the **docker image** is created.

- coverage==3.7.1

- mock==1.0.1

- nose==1.3.6

- psycopg2==2.6.1

- requests==2.8

- pytz==2015.7

- boto==2.38.0

- boto3==1.2.3

- analytics-python==1.1.0

- aiohttp

- google-api-python-client

- oauth2client

## Initial Set Up:

- `docker-compose up`

- `sh deploy.sh`

## To Do

- Implement ThreadPoolExecutor Architecture

- Unit Tests

- **Migration to Waywire API v2.0 will nulify the `external_id`s so these component will no longer work properly**