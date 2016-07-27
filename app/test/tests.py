import unittest
import os
import json
from datetime import datetime
from urllib.parse import urlparse
from unittest.mock import patch, MagicMock, mock_open
import requests
import psycopg2
from app.analytics import AnalyticsMixin
import app.compare
from app.compare import CompareTables
from app.config import DATABASE_URL, EMAILS, ENVIRONMENT
from app.loader import Loader, get_total_pages
from app.mail import SESClient
from app.migrate import create_ww_table, flush_ww_table
from app.utils import list_to_string, write_csv, clear_tmp, DATE_FMT
from app.item import set_url, BulkItem, WWItem
from app.sqs import SQSClient
from app.db import database_connection
from app.queries import (
    INSERT_BRAND, INSERT_CATEGORY, INSERT_SUBCATEGORY, SELECT_UNPUBLISHED_ITEMS,
    BULK_INSERT_CATEGORY, BULK_INSERT_SUBCATEGORY, BULK_INSERT_ITEMS)
from io import StringIO
import subprocess


class MockResponse(object):

    status_code = 200

    def __init__(self):
        with open('app/test/sample_output.json') as data:
            self.text = json.dumps(json.load(data))


def mock_cursor():
    m = MagicMock()
    m.execute.side_effect = Exception()
    return m


def mock_connection():
    m = MagicMock()
    m.set_session.return_value = None
    m.cursor.return_value = mock_cursor()
    return m


def mock_sqs():
    m = MagicMock()
    m.conn.return_value = mock_aws_conn()
    return m


def mock_aws_conn():
    m = MagicMock()
    m.get_queue.return_value = mock_queue()
    return m


def mock_queue():
    m = MagicMock()
    m.execute.side_effect = Exception()
    m.write.return_value = "Message written"


class DbMixin(object):

    db = database_connection()

    def _empty_tables(self):
        parsed = urlparse(DATABASE_URL)

        app_tables_query = """
        SELECT          table_name
        FROM            information_schema.tables
        WHERE           table_schema = 'public' AND
                        table_catalog = '{0}' AND
                        table_name != 'schema_version';""".format(parsed.path.strip('/'))
        cursor = self.db.cursor()
        cursor.execute(app_tables_query)
        tables = [r[0] for r in cursor.fetchall()]
        for t in tables:
            query = 'TRUNCATE TABLE {0} CASCADE;'.format(t)
            cursor.execute(query)
            self.db.commit()
        cursor.close()


class ListToStringTest(unittest.TestCase):

    def test_list_to_string(self):
        l = ['a', 'b', 'c']
        expected = '- a\n- b\n- c\n'
        self.assertEqual(expected, list_to_string(l))


class MockGet(object):

    def __init__(self, status=200):
        self.status_code = status

    def json(self):
        return {
            'opensearch:totalResults': {
                'content': 1
            }
        }

    @property
    def text(self):
        return "Error with service."


fake_data = {
    "entry": [
        {
            "id": {
                "content": "http://brandish.waywire.com/?id=broseph1"
            },
            "title": {
                "content": "Legit Title"
            }
        },
        {
            "id": {
                "content": "http://brandish.waywire.com/?id=broseph2"
            },
            "title": {
                "content": "Legit Title 2"
            }
        },
        {
            "id": {
                "content": "http://brandish.waywire.com/?id=broseph3"
            },
            "title": {
                "content": "Legit Title 3"
            }
        },
    ]
}


class MockPage(object):

    def __init__(self, status=200):
        self.status_code = status

    @property
    def text(self):
        return json.dumps(fake_data)


class LoaderTests(DbMixin, unittest.TestCase):

    def setUp(self):
        flush_ww_table()

    def test_get_total_pages(self):
        with patch.object(requests, 'get', return_value=MockGet()) as mr:
            pages = get_total_pages()
            self.assertTrue(mr.called)
            self.assertEqual(pages, 1)

        with patch.object(requests, 'get', return_value=MockGet(503)) as mr:
            pages = get_total_pages()
            self.assertTrue(mr.called)
            self.assertEqual(pages, 0)

    def test_process_bad_page(self):
        l = Loader()
        l.process_page("Bad json", 4)
        self.assertEqual(len(l.bad_pages), 1)
        self.assertEqual(l.bad_pages[0], 4)

    def test_handle_bad_pages(self):
        l = Loader()
        l.bad_pages = [4]
        with patch.object(requests, 'get', return_value=MockPage()) as mr:
            l.handle_bad_pages()
            self.assertTrue(mr.called)
        self.assertFalse(l.bad_pages)

    def test_run(self):
        l = Loader()
        l.pages = 1
        with patch.object(requests, 'get', return_value=MockPage()) as mr:
            l.run()
            self.assertTrue(mr.called)
        self.assertFalse(l.bad_pages)

        query = """
        SELECT COUNT (*) FROM ww_item;
        """

        with self.db.cursor() as c:
            c.execute(query)
            r = c.fetchone()
        self.assertEqual(r[0], 3)

    def test_migrate(self):
        with self.db.cursor() as c:
            c.execute("DROP TABLE ww_item;")

        create_ww_table()
        with self.db.cursor() as c:
            c.execute("select count(*) from ww_item;")
            r = c.fetchone()
        self.assertEqual(r[0], 0)


class Category(object):

    def __init__(self, *args):
        self.id, self.name = args


class MockWWPage(object):

    def __init__(self, status=200, path=''):
        self.status_code = status
        self.path = 'app/test/sample_for_compare.json'
        if path:
            self.path = path

    @property
    def text(self):
        with open(self.path, 'r') as f:
            return f.read()


class MockSESCon(object):

    def __init__(self, *args, **kwargs):
        return super().__init__()

    def send_raw_email(self, **kwargs):
        return "You sent a raw email."


class SESTest(unittest.TestCase):

    def test_send(self):
        msg = {"foo": "bar"}
        cli = SESClient()
        with patch.object(SESClient, 'conn', return_value=MockSESCon()) as me:
            cli.send_message(msg)
            self.assertTrue(me.called)


class MockSQSCon(object):

    def __init__(self, *args, **kwargs):
        return super().__init__()

    def write_message(self, **kwargs):
        return "You sent a message to the queue."


class SQSTest(unittest.TestCase):

    def test_send(self):
        msg = {"foo": "bar"}
        cli = SQSClient()
        with patch.object(SQSClient, 'conn', return_value=MockSQSCon()) as mq:
            cli.write_message(msg)
            self.assertTrue(mq.called)


class CompareTest(DbMixin, unittest.TestCase):

    def setUp(self):
        self._empty_tables()
        # Setup some categories
        cats = json.dumps([
            {'name': 'Professional Sports'},
            {'name': 'Luxury'},
            {'name': 'Electronics'},
            {'name': "Men's Apparel"}
        ])
        with self.db.cursor() as c:
            c.execute(BULK_INSERT_CATEGORY, (cats, ))
            rows = c.fetchall()
        for row in rows:
            if row[1] == 'Professional Sports':
                self.prosports = Category(*row)
            elif row[1] == 'Luxury':
                self.luxury = Category(*row)
            elif row[1] == 'Electronics':
                self.electronics = Category(*row)
            elif row[1] == "Men's Apparel":
                self.mapparel = Category(*row)
        with self.db.cursor() as c:
            c.execute("SELECT COUNT (*) FROM categories_category;")
            r = c.fetchone()
        self.assertEqual(r[0], 4)

        subcats = json.dumps([
            {'name': 'Audio', 'category_id': self.electronics.id},
            {'name': 'Boating', 'category_id': self.luxury.id},
            {'name': 'MLB', 'category_id': self.prosports.id},
            {'name': 'World Cup', 'category_id': self.prosports.id},
            {'name': 'NBA', 'category_id': self.prosports.id},
            {'name': 'Formal', 'category_id': self.mapparel.id},
        ])
        with self.db.cursor() as c:
            c.execute(BULK_INSERT_SUBCATEGORY, (subcats, ))
            c.execute("SELECT COUNT (*) FROM categories_subcategory;")
            r = c.fetchone()
        self.assertEqual(r[0], 6)

        query = """
        INSERT INTO brand_brand (name)
        VALUES      (%(name)s)
        RETURNING   id;
        """
        with self.db.cursor() as c:
            c.execute(query, {'name': 'MLB'})
            r = c.fetchall()
        self.brand_id = r[0][0]

        # Load items
        l = Loader()
        l.pages = 1
        with patch.object(requests, 'get', return_value=MockWWPage()) as mr:
            l.run()
            self.assertTrue(mr.called)

        with self.db.cursor() as c:
            c.execute("SELECT COUNT (*) FROM ww_item;")
            r = c.fetchone()
        self.assertEqual(r[0], 10)

    def test_bulk_item(self):
        wwitems = [i for i in BulkItem.all_to_publish()]
        self.assertEqual(len(wwitems), 10)
        for item in wwitems:
            self.assertTrue(isinstance(item, WWItem))
        item_0 = wwitems[0]
        self.assertEqual(
            item_0.waywire_id,
            "http://brandish.waywire.com/api/content/show?id=FNG3F71FC8QXBHSD&key=")
        self.assertEqual(
            item_0.source['title']['content'],
            "Amy Schumer Rejects Glamour's Plus-Size Label")

        # test the WWItem methods.
        expected_tags = {
            'country': 'usa',
            'category': 'Television',
            'brand': 'The Tonight Show Starring Jimmy Fallon',
            'subcategory': 'Talk Shows',
            'adult': False,
            'brandish_select': False,
            'brandish_feed': False,
            'parsed_tag': 'Television-Talk_Shows'
        }
        self.assertEqual(item_0.get_tags, expected_tags)
        self.assertFalse(item_0.is_valid())
        self.assertEqual(item_0.get_duration(), '97')

        params = item_0.get_params()
        self.assertFalse(params['brand_id'])
        self.assertFalse(params['category_id'])
        self.assertFalse(params['subcategory_id'])
        self.assertEqual(params['brand_name'], expected_tags['brand'])
        self.assertTrue(params['approved'])
        self.assertFalse(params['adult'])
        self.assertEqual(
            params['thumbnail'],
            "https://s3.amazonaws.com/item.thumbnail/content/FNG3F71FC8QXBHSD/regular.jpg")
        self.assertEqual(params['url'], "https://player.waywire.com/?id=FNG3F71FC8QXBHSD")
        self.assertEqual(params['duration'], '97')
        self.assertEqual(params['title'], "Amy Schumer Rejects Glamour's Plus-Size Label")
        self.assertFalse(params['brandish_select'])
        self.assertFalse(params['brandish_feed'])
        self.assertEqual(
            params['waywire_id'],
            "http://brandish.waywire.com/api/content/show?id=FNG3F71FC8QXBHSD&key=")
        self.assertEqual(params['country'], 'usa')
        description = "Comedy, The, Tonight, Show,"
        self.assertTrue(params['description'].startswith(description))
        self.assertEqual(params['source'], json.dumps(item_0.source))

        # Check on a valid item
        for item in wwitems:
            wwid = "http://brandish.waywire.com/api/content/show?id=T0LKMF341NSC2LBC&key="
            if item.waywire_id == wwid:
                self.assertTrue(item.is_valid())
                self.assertTrue(item.get_brand_id(), self.brand_id)
                self.assertTrue(item.get_params()['brandish_feed'])
                self.assertTrue(item.get_params()['brandish_select'])
                self.assertTrue(item.get_params()['adult'])

    def test_compare(self):
        # Test the entire compare flow.
        # Add an existing row on item_item that isn't on ww_item
        with open('app/test/sample_to_delete_output.json', 'r') as f:
            data = f.read()
        item = WWItem(None, json.loads(data))
        with self.db.cursor() as c:
            c.execute(BULK_INSERT_ITEMS, (json.dumps([item.get_params()]), ))
            r = c.fetchall()
        self.assertTrue(r)
        old_item_id = r[0][0]

        query = """
        SELECT COUNT (*) FROM item_item;
        """

        with self.db.cursor() as c:
            c.execute(query)
            r = c.fetchone()
        self.assertEqual(r[0], 1)

        # Compare
        c = CompareTables()
        csv_args = ("path/filename.csv", "filename.csv", True)
        with patch.object(app.compare, 'write_csv', return_value=csv_args) as mw:
            with patch.object(app.compare, 'clear_tmp', return_value=None) as mclr:
                with patch.object(SESClient, 'send_message', return_value='fake email') as me:
                    with patch.object(SQSClient, 'write_message', return_value='fake msg') as mm:
                        with patch.object(AnalyticsMixin, 'track_item', return_value='None') as mt:
                            c.run()
                            self.assertTrue(mt.called)
                            self.assertTrue(mw.called)
                            self.assertTrue(mclr.called)
                            self.assertTrue(me.called)
                            self.assertTrue(mm.called)

        with self.db.cursor() as c:
            c.execute(query)
            r = c.fetchone()
        self.assertEqual(r[0], 5)

        # Make sure the existing item got deleted
        query = """
        SELECT * FROM item_item WHERE waywire_id = %s;
        """
        with self.db.cursor() as c:
            c.execute(query, (item.source['id']['content'], ))
            r = c.fetchall()
        self.assertFalse(r)

        # Verify ww_item is empty
        query = """
        SELECT COUNT (*) FROM ww_item;
        """

        with self.db.cursor() as c:
            c.execute(query)
            r = c.fetchone()
        self.assertEqual(r[0], 0)

    def test_update(self):
        # Clear out existing items first.
        with self.db.cursor() as c:
            c.execute("DELETE FROM item_item; DELETE FROM ww_item;")
        # Test the update flow.
        # Add an existing row on item_item that isn't on ww_item
        with open('app/test/sample_to_update.json', 'r') as f:
            data = f.read()
        item = json.loads(data).copy()
        old_text = "These training gis' power levels? Over 9000. #DealWithIt"
        item['entry'][0]['content']['content'] = old_text
        old_item = WWItem(None, item['entry'][0])
        old_cat = [
            {
              "label": "Electronics-Audio",
              "term": "Electronics-Audio"
            },
            {
              "label": "country.usa",
              "term": "country.usa"
            },
            {
              "label": "brand.FakeBrand",
              "term": "brand.FakeBrand"
            },
            {
              "label": "better_home",
              "term": "better_home"
            },
            {
              "label": "language.english",
              "term": "language.english"
            }
        ]
        item['entry'][1]['category'] = old_cat
        invalid_item = WWItem(None, item['entry'][1])
        with self.db.cursor() as c:
            c.execute(
                BULK_INSERT_ITEMS,
                (json.dumps([old_item.get_params(), invalid_item.get_params()]), ))
            r = c.fetchall()
        old_id = r[0][0]

        l = Loader()
        l.pages = 1
        with patch.object(requests, 'get',
                          return_value=MockWWPage(path='app/test/sample_to_update.json')) as mr:
            l.run()
            self.assertTrue(mr.called)
        c = CompareTables()
        csv_args = ("path/filename.csv", "filename.csv", True)
        with patch.object(app.compare, 'write_csv', return_value=csv_args) as mw:
            with patch.object(app.compare, 'clear_tmp', return_value=None) as mclr:
                with patch.object(SESClient, 'send_message', return_value='fake email') as me:
                    with patch.object(SQSClient, 'write_message', return_value='fake msg') as mm:
                            c.update_items()
                            self.assertTrue(mw.called)
                            self.assertTrue(mclr.called)
                            self.assertTrue(me.called)
                            self.assertTrue(mm.called)

        with self.db.cursor() as c:
            c.execute("select description from item_item where id = %s;", (old_id, ))
            r = c.fetchall()
        self.assertEqual(
            r[0][0], "Next time on Dragon Ball Z. HAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH!")
        flush_ww_table()
        self.assertFalse(list(BulkItem.all_to_update()))
        self.assertFalse(list(BulkItem.all_to_publish()))

    def test_csv_write(self):
        write_csv([i for i in BulkItem.all_to_publish() if not i.is_valid()])
        filename = 'invalid_items_{}.csv'.format(datetime.utcnow().strftime(DATE_FMT))
        path = '{}/tmp/invalid_items_{}.csv'.format(os.getcwd(), filename)
        list_dir = os.listdir('{}/tmp'.format(os.getcwd()))
        self.assertTrue(filename in list_dir)
        clear_tmp()

    def test_analytics(self):
        flush_ww_table()
        with self.db.cursor() as c:
            c.execute("delete from item_item;")
        mr = MockWWPage(path='app/test/sample_for_analytics.json')
        l = Loader()
        l.pages = 1
        with patch.object(requests, 'get', return_value=mr) as mckr:
            l.run()
            self.assertTrue(mckr.called)

        c = CompareTables()
        with patch.object(SESClient, 'send_message', return_value='fake email') as me:
            with patch.object(SQSClient, 'write_message', return_value='fake msg') as mm:
                with patch.object(AnalyticsMixin, 'track_item', return_value='None') as mt:
                    c.publish_items()
                    with self.db.cursor() as c:
                        c.execute("select id, waywire_id from item_item;")
                        r = c.fetchall()
                    self.assertFalse(me.called)  # No invalid items.
                    self.assertTrue(mm.called)
                    self.assertTrue(mt.called)
                    mt.assert_called_with(r[0][0], r[0][1])
