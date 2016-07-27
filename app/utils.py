import csv
import itertools
import logging
import os
from .config import ENVIRONMENT, SUPPORT_EMAIL, EMAILS
from datetime import datetime
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


logger = logging.getLogger('brandish')


DATE_FMT = "%Y-%m-%d"


def list_to_string(l):
    nl = ['- {}\n'.format(el) for el in l]
    strl = ''.join(nl)
    return strl


def write_csv(invalid_items=[], update=False):
    """
    Writes a csv for any invalid or bad items that show up during the
    publish step of the YouTubeWorker process.
    """
    filename = "invalid_vs_items_{}.csv".format(datetime.utcnow().strftime(DATE_FMT))
    if update:
        filename = "invalid_update_vs_items{}.csv".format(datetime.utcnow().strftime(DATE_FMT))
    path = "{0}/tmp/{1}".format(os.getcwd(), filename)
    try:
        with open(path, 'w') as f:
            fieldnames = ['waywire_id', 'player_URL', 'waywire_URL']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in invalid_items:
                data = {
                    'waywire_id': invalid_items[item],
                    'player_URL': "https://player.waywire.com/?id={}".format(invalid_items[item]),
                    'waywire_URL': "http://brandish.waywire.com/admin/manage/postings/item/{}".format(invalid_items[item])
                }
                # data.update(item.get_tags)
                writer.writerow(data)
        return filename, path, update
    except FileNotFoundError:  # pragma: no cover
        logger.exception("Error writing invalid item csv.")
        return None, None, False


def clear_tmp():
    """
    Removes any csv in the tmp directory.
    """
    try:
        path = "rm {}/tmp/*.csv".format(os.getcwd())
        return subprocess.run([path], shell=True, check=True)
    except subprocess.CalledProcessError:  # pragma: no cover
        logger.exception("Error clearing out tmp directory.")
        return None


def build_message(filename=None, path=None, update=False):
    """
    Builds a MIME message with a csv attachment.
    """
    msg = MIMEMultipart()
    subject = 'Brandish {} VS Worker - Invalid Items'.format(ENVIRONMENT)
    if update:
        subject = 'Brandish {} VS Worker - Invalid Updated Items'.format(ENVIRONMENT)
    msg['Subject'] = subject
    msg['From'] = SUPPORT_EMAIL
    msg['To'] = ', '.join(EMAILS)
    text = """
    Please find attached a spreadsheet of items that could not be updated from YouTube.
    Common reasons for an item not being updated:
    - Video has gone private or deleted
    - Video is from Vimeo (We're working on that)
    """
    msg.preamble = text
    msg.attach(MIMEText(text, 'plain'))
    if filename and path:  # pragma: no cover
        try:
            with open(path, 'r') as fp:
                attachment = MIMEText(fp.read(), _subtype='csv')
            attachment.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(attachment)
        except FileNotFoundError:  # pragma: no cover
            logger.exception("Error attaching file.")
    return msg.as_bytes()


def gen_peek(iterable):  # pragma: no cover
    iterator = iter(iterable)
    try:
        val = next(iterator)
    except StopIteration:
        return None
    return itertools.chain([val], iterable)
