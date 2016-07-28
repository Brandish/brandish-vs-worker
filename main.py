from app.youtube_worker import YouTubeWorker
from app.config import WAYWIRE_API_KEY, DATABASE_URL, WAIT_TIME, LOADER_WAIT_TIME, ENVIRONMENT
import logging
import time

logger = logging.getLogger('brandish-vs-worker')

def compare():

    y = YouTubeWorker()

    if ENVIRONMENT != 'testing':
        while True:
            y.run()  # Fetches statistical information from YouTube
            print("Going to sleep for: {} seconds.".format(LOADER_WAIT_TIME*2))
            time.sleep(LOADER_WAIT_TIME*2)
    else:
        while True:
            print("OK.")
            time.sleep(WAIT_TIME)

if __name__ == "__main__":
    compare()
