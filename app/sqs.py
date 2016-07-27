from boto3 import client
import json
import logging
from app.config import AWS_SQS_URL


logger = logging.getLogger('brandish')


class SQSClient(object):

    def conn(self):
        return client('sqs')  # pragma: no cover

    def write_message(self, msg_dict):
        msg = json.dumps(msg_dict)
        # try:
        #     self.conn().send_message(QueueUrl=AWS_SQS_URL, MessageBody=msg)
        # except Exception:
        #     logger.exception('Error writing to q: {}'.format(msg))
