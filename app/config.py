import os
import logging
from logging.handlers import SysLogHandler


WAYWIRE_URL = os.getenv('WAYWIRE_URL')
assert WAYWIRE_URL

WAYWIRE_FIND_URL = os.getenv('WAYWIRE_FIND_URL')
assert WAYWIRE_FIND_URL

WAYWIRE_API_KEY = os.getenv('WAYWIRE_API_KEY')
assert WAYWIRE_API_KEY

GOOGLE_DEV_KEY = os.getenv('GOOGLE_DEV_KEY')
assert GOOGLE_DEV_KEY

# DATABASE_URL = os.getenv(
   # 'DATABASE_URL',
   # 'postgres://postgres:postgres@{0}:5432/postgres'.format(
   #     os.getenv('DB_PORT_5432_TCP_ADDR', None)))
DATABASE_URL = os.getenv('DATABASE_URL', 'postgres://brandish:br4ndish2016@brandish-db-production.ctgrfahcuiik.us-west-2.rds.amazonaws.com:5432/brandish')
assert DATABASE_URL

WAIT_TIME = int(os.getenv('WAIT_TIME', '20000'))
assert WAIT_TIME

LOADER_WAIT_TIME = int(os.getenv('LOADER_WAIT_TIME', 1800))
assert LOADER_WAIT_TIME

ENVIRONMENT = os.getenv('ENVIRONMENT', 'staging')
assert ENVIRONMENT

SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', '')
assert SUPPORT_EMAIL

EXTRA_EMAILS = os.getenv('EXTRA_EMAILS', '')

AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'MsLjlH3x1P7n0jnYQremQBbqAOm7anyz8DdngQMZ')
assert AWS_SECRET_ACCESS_KEY

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'AKIAJDEF3AKHSIMO7G2Q')
assert AWS_ACCESS_KEY_ID

AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
assert AWS_DEFAULT_REGION

AWS_SQS_URL = os.getenv('AWS_SQS_URL', 'https://sqs.us-west-2.amazonaws.com/717749257474/brandish-test')
assert AWS_SQS_URL

AWS_SES_ARN = os.getenv('AWS_SES_ARN', '')
assert AWS_SES_ARN

SEGMENT_KEY = os.getenv('SEGMENT_KEY', '')

PAGINATE_BY = int(os.getenv('PAGINATE_BY', 50))

MAX_WORKERS = int(os.getenv('MAX_WORKERS', 5))

EMAILS = [SUPPORT_EMAIL]
if EXTRA_EMAILS != '':
    EMAILS += EXTRA_EMAILS.split(',')

DATETIME_FMT = '%Y-%m-%dT%H:%M:%SZ'

# Setup logger
handler = logging.NullHandler() if ENVIRONMENT == 'testing' else SysLogHandler(address=('app_syslog', 514), facility='local5')
formatter = logging.Formatter(
    'Python: { "loggerName":"%(name)s", "environment": "' + ENVIRONMENT +'", "asciTime":"%(asctime)s", "logRecordCreationTime":'
    '"%(created)f", "levelNo":"%(levelno)s", "time":"%(msecs)d", "levelName":"%(levelname)s", '
    '"message":"%(message)s"}')
handler.formatter = formatter
logger = logging.getLogger('brandish-vs-worker')
logger.addHandler(handler)
logger.setLevel(logging.INFO)
