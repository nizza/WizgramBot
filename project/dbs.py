import rethinkdb as rdb
import threading
import queue
import datetime as dt
import json
from functools import partial
import pytz

from .logs import logger

TABLE = 'telegram'
reco_queue = queue.Queue()

tz = pytz.timezone('Europe/Paris')


def add_reco(user, reco, img):
    img.seek(0)
    reco_queue.put(('reco', (user, json.dumps(reco), img.read())))


def add_feedback(user, feedback):
    reco_queue.put(('feedback', (user, feedback)))


def save_feedback(user, feedback, conn):
    req = (rdb.table(TABLE)
              .get_all(user, index='user')
              .order_by(rdb.desc('uploaded_at'))[0]
              .update({'feedback': int(feedback)})
           )

    return safe_index(req, conn)


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
        else:
            user, feedback = data
            _ = save_feedback(user, feedback, conn)


def start_thread(host, port, db, **kwargs):

    w = partial(worker, host=host, port=port, db=db)
    t = threading.Thread(target=w)
    t.daemon = True
    t.start()
