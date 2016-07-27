from .db import database_connection
from .queries import CREATE_WW_TABLE, DELETE_WW_ITEMS
import logging

logger = logging.getLogger('brandish')

def create_ww_table():
    db = database_connection()
    try:
        with db.cursor() as c:
            c.execute(CREATE_WW_TABLE)
    except Exception:  # pragma: no cover
        logger.exception('query: {}'.format(CREATE_WW_TABLE))


def flush_ww_table():
    db = database_connection()
    try:
        with db.cursor() as c:
            c.execute(DELETE_WW_ITEMS)
    except Exception:  # pragma: no cover
        logger.exception('query: {}'.format(DELETE_WW_ITEMS))
