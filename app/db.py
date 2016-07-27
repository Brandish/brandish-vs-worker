import logging
import psycopg2
from urllib.parse import urlparse
from .config import DATABASE_URL


def database_connection():
    parsed = urlparse(DATABASE_URL)
    print(parsed)
    user = parsed.username
    password = parsed.password
    host = parsed.hostname
    port = parsed.port
    database = parsed.path.strip('/')
    connection = psycopg2.connect(
        host=host, port=port, user=user, password=password, database=database)
    connection.set_session(autocommit=True)

    return connection


logger = logging.getLogger('brandish')


class DBMixin(object):

    """Helper mixin."""

    db = database_connection()

    def run_delete(self, query, **kwargs):
        try:
            with self.db.cursor() as c:
                c.execute(query, kwargs)
        except Exception:  # pragma: no cover
            logger.exception('query: {} \n params: {}'.format(query, kwargs))

    def run_query(self, query):
        try:
            with self.db.cursor() as c:
                c.execute(query)
                r = c.fetchall()
        except Exception:  # pragma: no cover
            logger.exception('query: {}'.format(query))
            r = None
        return r
