import boto.ses
from boto3 import client
import botocore
from .config import (
    SUPPORT_EMAIL, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY,
    AWS_ACCESS_KEY_ID, EXTRA_EMAILS, AWS_SES_ARN
)
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging

logger = logging.getLogger('brandish')

def send_email_msg(to=[], subject=None, text=None, html=None):  # pragma: no cover
    conn = boto.ses.connect_to_region(
        AWS_DEFAULT_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

    format = 'html' if html else 'text'

    try:
        conn.send_email(
            source=SUPPORT_EMAIL,
            subject=subject,
            body=None,
            to_addresses=to,
            cc_addresses=None,
            bcc_addresses=None,
            format=format,
            reply_addresses=None,
            return_path=None,
            text_body=text,
            html_body=html
        )
    except boto.ses.exceptions.SESError:
        err_msg = 'Could not send "{0}" email to {1}.'.format(subject, ', '.join(to))
        logger.exception(err_msg)
        raise


class SESClient(object):

    def conn(self):
        return client('ses')  # pragma: no cover

    def send_message(self, raw_msg):
        try:
            self.conn().send_raw_email(
                RawMessage={
                    'Data': raw_msg
                },
                SourceArn=AWS_SES_ARN
            )
        except botocore.exceptions.ClientError:  # pragma: no cover
            logger.exception("Error sending csv email.")
