import requests
from .db import database_connection
from .queries import (SELECT_ITEMS, BULK_UPDATE_ITEM_VIEW_COUNT)
from .db import DBMixin
from .config import WAYWIRE_API_KEY, WAYWIRE_FIND_URL, GOOGLE_DEV_KEY
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.tools import argparser
from .utils import write_csv, clear_tmp, build_message, gen_peek
from .mail import SESClient
import logging
import time
import json
import numbers

URL = WAYWIRE_FIND_URL
DEVELOPER_KEY = GOOGLE_DEV_KEY
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_PAGE_SIZE = 50

logger = logging.getLogger('brandish-vs-worker')
sescli = SESClient()

class YouTubeWorker(DBMixin, object):

    waywire_maps_br = {}
    youtube_maps_ww = {}
    nonexistent_ids = {}
    external_ids_to_test = {}

    """
    Fetches Statistical information for all 
    the items into the item_item table.
    """
    def __init__(self):
        self.waywire_maps_br = {}
        self.youtube_maps_ww = {}
        self.nonexistent_ids = {}
        self.external_ids_to_test = {}

    def run(self):
        # try:

            # We get all the Items in the DB
            with self.db.cursor() as cursor:
                start = time.time()
                cursor.execute(SELECT_ITEMS)
                rows = cursor.fetchall()
                if rows:

                    print("Going to fetch {} YouTube videos.".format(len(rows)))
                    self.waywire_maps_br = {}
                    self.youtube_maps_ww = {}
                    # We need to iterate the Items from the DB
                    # to fetch data from Waywire. For next versions
                    # of the API we should just make one API call
                    # instead of having them in a loop ¬_¬
                    # We'll use a 50 item page size based on YouTube
                    # API limits
                    current_page = 1
                    youtube_ids = []
                    for row in rows:
                        waywire_url = row[2] # url field
                        waywire_video_id = waywire_url.replace('https://player.waywire.com/?id=', '')
                        waywire_json = row[3] # source field
                        external_id = waywire_json['magnify:externalid']['content']

                        # Handling Vimeo ID format
                        if not external_id.isdigit() :
                            # Data Structures for convenience
                            # ID-mapping
                            self.waywire_maps_br[waywire_video_id] = row[0]
                            self.youtube_maps_ww[external_id] = waywire_video_id
                            # This external ID is going to disappear in V2.0
                            youtube_ids.append(external_id)

                            if len(rows) >= 50:
                                # We use this to control the 50 
                                # element buffer
                                if current_page % YOUTUBE_PAGE_SIZE == 0:
                                    # We need this to make less calls to
                                    # Google APIs
                                    youtube_ids_str = ",".join(youtube_ids)
                                    youtube_ids = []
                                    self.fetch_and_update_items(youtube_ids_str)
                                current_page += 1
                        
                    if len(rows) < 50:
                        youtube_ids_str = ",".join(youtube_ids)
                        youtube_ids = []
                        self.fetch_and_update_items(youtube_ids_str)
                    
                if len(self.nonexistent_ids) > 0:
                    sescli.send_message(build_message(*write_csv(self.nonexistent_ids, update=True)))
                    clear_tmp()

                end = time.time()
                run_time = end - start
                print("Finished polling YouTube API. Total run time: {} seconds".format(run_time))

        # except Exception as e:
        #     print("Failed to get Items.")
        #     print(e)
        

    def youtube_search(self, ids=''):
        # print("Fetching YouTube Information")
        youtube = build(
            YOUTUBE_API_SERVICE_NAME, 
            YOUTUBE_API_VERSION,
            developerKey=DEVELOPER_KEY)

        # Call the search.list method to retrieve results matching the specified
        # query term.
        search_response = youtube.videos().list(
            id=ids,
            part="id, statistics"
        ).execute()

        search_videos = []
        # Merge video ids
        for search_result in search_response.get("items", []):
            search_videos.append(search_result)
        return search_videos

    def fetch_and_update_items(self, ids=''):
        try:
            # API Call to YouTube
            # THREAD-BLOCKING: REMOVE ASAP
            youtube_videos = self.youtube_search(ids=ids)

            items_to_update = []
            # We need to iterate the youtube videos
            # to setup the new data structures for
            # Item batch update
            # external_ids_to_test holds the IDs
            # for the items that we retrieved from YT

            count = 0
            for youtube_video in youtube_videos:
                external_id = youtube_video['id']
                view_count = youtube_video['statistics']['viewCount']
                waywire_id = self.youtube_maps_ww[external_id]
                item_to_update = {
                    "id": self.waywire_maps_br[waywire_id],
                    "view_count": int(view_count),
                    "waywire_video_id": waywire_id,
                    "external_video_id": external_id,
                    "external_video_url": "https://www.youtube.com/watch?v=" + external_id
                }
                items_to_update.append(item_to_update)
                self.external_ids_to_test[external_id] = True
                count += 1

            if count != YOUTUBE_PAGE_SIZE:
                for ext_id in self.youtube_maps_ww.keys():
                    if ext_id not in self.external_ids_to_test:
                        self.nonexistent_ids[ext_id] = self.youtube_maps_ww[ext_id]

            # DB construction that allows iteration over a 
            # data structure for multiple SQL statements
            with self.db.cursor() as cursor:
                cursor.executemany(BULK_UPDATE_ITEM_VIEW_COUNT, tuple(items_to_update))
        except Exception as exc:
            print("YouTube API Call Failed")
            print(exc)

