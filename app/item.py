import logging
import json
from .queries import (
    BRAND_BY_NAME, CATEGORY_BY_NAME, SUBCATEGORY_BY_NAME,
    DELETE_ITEM, SELECT_ITEMS_TO_PUBLISH, SELECT_ITEMS_TO_UPDATE)
from datetime import datetime
from app.analytics import AnalyticsMixin
from app.config import DATETIME_FMT
from app.db import DBMixin


logger = logging.getLogger('brandish')


def set_url(v):
    if v.startswith('//'):
        v = 'https:' + v
    return v


def parse_tags(cat_dict):
    data = {
        'country': '',
        'category': '',
        'brand': '',
        'subcategory': '',
        'adult': False,
        'brandish_select': False,
        'brandish_feed': False,
        'parsed_tag': ''
    }
    for cat in cat_dict:
        label = cat['label']
        if label.startswith("Internal."):
            continue  # pragma: no cover
        elif label.startswith('brand.'):
            data['brand'] = label[6:].replace('_', ' ')
        elif '-' in label:
            data['parsed_tag'] = label
            categories = label.split('-')
            data['category'] = categories[0].replace('_', ' ')
            data['subcategory'] = '-'.join(categories[1:]).replace('_', ' ')
        elif label.startswith('adult.'):
            data['adult'] = True
        elif label.startswith('country.'):
            data['country'] = label[8:]
        elif 'brandish.select' in label:
            data['brandish_select'] = True
        elif 'brandish.feed' in label:
            data['brandish_feed'] = True
    return data


class WWItem(DBMixin):

    """
    Class that represents rows in the ww_item table.
    """

    def __init__(self, *args):
        self.waywire_id, self.source = args

    @property
    def get_tags(self):
        return parse_tags(self.source['category'])

    def is_valid(self):
        cat = self.get_category_id()
        subcat = self.get_subcategory_id()
        return bool(cat and subcat)

    def fetch_id(self, query, **params):
        val = None
        try:
            with self.db.cursor() as c:
                c.execute(query, params)
                row = c.fetchone()
                if row:
                    val = row[0]
        except Exception:  # pragma: no cover
            logger.exception('query: {} \n params: {}'.format(query, params))
        return val

    def get_category_id(self):
        cat = self.get_tags['category']
        if cat:
            cat_permutations = [cat, cat.replace(' and ', ' & ')]
            for c in cat_permutations:
                params = {"name": c}
                row_id = self.fetch_id(CATEGORY_BY_NAME, **params)
                if row_id:
                    return row_id
        return None

    def get_subcategory_id(self):
        if self.get_category_id():
            subcat = self.get_tags['subcategory']
            subcat_permutations = [subcat, subcat.replace(' and ', ' & ')]
            for s in subcat_permutations:
                params = {"name": s, 'category_id': self.get_category_id()}
                row_id = self.fetch_id(SUBCATEGORY_BY_NAME, **params)
                if row_id:
                    return row_id
        return None

    def get_brand_id(self):
        brand_name = self.get_tags['brand']
        if brand_name:
            brand_permutations = [
                brand_name,
                brand_name.replace('dot', '.'),
                brand_name.replace(' and ', ' & '),
                brand_name.replace('dot', '.').replace(' and ', ' & ')]
            for b in brand_permutations:
                params = {'name': b}
                row_id = self.fetch_id(BRAND_BY_NAME, **params)
                if row_id:
                    return row_id
        return None

    def get_duration(self):
        # Because durations can be null as of 4/11/2016
        ww_duration = self.source['media:html5']['duration']
        return ww_duration if ww_duration else 0

    def get_params(self):
        update_time = datetime.utcnow().strftime(DATETIME_FMT)
        params = {
            'brand_id': self.get_brand_id(),
            'category_id': self.get_category_id(),
            'subcategory_id': self.get_subcategory_id(),
            'brand_name': self.get_tags['brand'],
            'approved': True,
            'approval_date': update_time,
            'updated_date': update_time,
            'adult': self.get_tags['adult'],
            'thumbnail': self.source['media:thumbnail']['url'],
            'url': set_url(self.source['media:html5']['url']),
            'duration': self.get_duration(),
            'title': self.source['title']['content'],
            'brandish_select': self.get_tags['brandish_select'],
            'brandish_feed': self.get_tags['brandish_feed'],
            'waywire_updated_date': self.source['updated']['content'],
            'waywire_published_date': self.source['published']['content'],
            'waywire_id': self.source['id']['content'],
            'country': self.get_tags['country'],
            'description': self.source['content']['content'],
            'source': json.dumps(self.source)
        }
        return params


class TmpItem(WWItem):

    def __init__(self, *args):
        self.id, self.waywire_id, self.source = args

    def get_params(self):
        default = super().get_params()
        params = {'item_id': self.id, 'params': json.dumps(default)}
        return params


class BulkItem(DBMixin):

    """
    Class that serves as a bulk wrapper around records either in ww_item
    or item_item.
    """

    get_publish_query = SELECT_ITEMS_TO_PUBLISH
    get_update_query = SELECT_ITEMS_TO_UPDATE

    @classmethod
    def all_to_publish(cls):
        try:
            with cls.db.cursor() as c:
                c.execute(cls.get_publish_query)
                r = c.fetchall()
        except Exception:  # pragma: no cover
            logger.exception(
                'Failed to retrieve items to publish: {}\n'.format(cls.get_publish_query))
            return []
        else:
            return (WWItem(*row) for row in r)

    @classmethod
    def all_to_update(cls):
        try:
            with cls.db.cursor() as c:
                c.execute(cls.get_update_query)
                r = c.fetchall()
        except Exception:  # pragma: no cover
            logger.exception(
                'Failed to retrieve items to update: {}\n'.format(cls.get_update_query))
            return []
        else:
            return (TmpItem(*row) for row in r)
