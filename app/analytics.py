from app.config import SEGMENT_KEY
import analytics
import logging
from datetime import datetime


analytics.write_key = SEGMENT_KEY
logger = logging.getLogger('brandish')


class AnalyticsMixin(object):

    def _track(self, *args, **kwargs):
        try:
            analytics.track(*args, kwargs)
        except Exception as e:  # pragma: no cover
            logger.exception({
                'platform': 'Segment Analytics',
                'detail': 'Error sending over analytics',
                'traceback': str(e.__traceback__)})

    def track_item(self, item_id, ww_id):
        args = [item_id, 'Video Created Or Updated']
        kwargs = {
            'waywire_id': ww_id,
            'updated_date': datetime.utcnow()
        }
        self._track(*args, **kwargs)

    def bulk_track(self, params):
        for param in params:
            self.track_item(param[0], param[1])
