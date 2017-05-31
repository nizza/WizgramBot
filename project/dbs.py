import rethinkdb as rdb
import threading
import queue
import datetime as dt
import json
from functools import partial
import pytz

from .utils import safe_index
from .logs import logger

TABLE = 'telegram'
FEEDBACK_TABLE = 'feedback'
reco_queue = queue.Queue()

tz = pytz.timezone('Europe/Paris')


def add_reco(user, reco, img):
    img.seek(0)
    reco_queue.put(('reco', (user, json.dumps(reco), img.read())))


def add_app_feedback(user, feedback):
    reco_queue.put(('feedback_app', (user, feedback)))


def add_feedback(user, feedback):
    reco_queue.put(('feedback', (user, feedback)))


def save_app_feedback(user, feedback, conn):
    feedback = {
        'user': user,
        'feedback': feedback,
        'app': 'telegram',
        'uploaded_at': dt.datetime.now(tz=tz)
    }
    req = rdb.table(FEEDBACK_TABLE).insert(feedback)
    try:
        safe_index(req, conn)
    except rdb.ReqlNonExistenceError:
        logger.warning('Could not save feedback...')


def save_feedback(user, feedback, conn):
    req = (rdb.table(TABLE)
              .get_all(user, index='user')
              .order_by(rdb.desc('uploaded_at'))[0]
              .update({'feedback': int(feedback)})
           )
    try:
        safe_index(req, conn)
    except rdb.ReqlNonExistenceError:
        logger.warning('Could not save feedback...')


def save_reco(user, reco, img, conn):
    date = dt.datetime.now(tz=tz)

    req = rdb.table(TABLE).insert({
        'uploaded_at': date,
        'user': user,
        'img': img,
        'reco': json.loads(reco),
        'feedback': None
    })
    return safe_index(req, conn)


def worker(host, port, db):
    logger.info('Connecting to rethinkdb ...')
    conn = rdb.connect(host, port, db, timeout=10)
    logger.info('connected !')

    while True:
        data_type, data = reco_queue.get()
        if data_type == 'reco':
            user, reco, img = data
            _ = save_reco(user, reco, img, conn)
        elif data_type == 'feedback':
            user, feedback = data
            save_feedback(user, feedback, conn)
        elif data_type == 'feedback_app':
            user, feedback = data
            save_app_feedback(user, feedback, conn)
        else:
            raise NotImplementedError("Data type '{}' not implemented".format(data_type))

def start_thread(host, port, db, **kwargs):

    w = partial(worker, host=host, port=port, db=db)
    t = threading.Thread(target=w)
    t.daemon = True
    t.start()
