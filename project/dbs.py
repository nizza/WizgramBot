import sqlite3
import os
import threading
import queue
import datetime as dt
import json

from .logs import logger

db_name = 'users.db'
db_folder = (os.environ.get('DB_PATH') or
             os.path.join(os.path.dirname(__file__),  '..', 'db'))
db_path = os.path.join(db_folder, db_name)

reco_queue = queue.Queue()


def create_table():
    logger.info('Connecting to {}'.format(db_path))
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE users
                 (date DATE , user text, feedback INT,
                  reco text, img BLOB)
              ''')
    conn.commit()
    conn.close()


def add_reco(user, reco, img):
    img.seek(0)
    reco_queue.put(('reco', (user, json.dumps(reco), img.read())))


def add_feedback(user, feedback):
    reco_queue.put(('feedback', (user, feedback)))


def save_feedback(user, feedback, c):
    c.execute('''
    UPDATE users
       SET feedback = {feedback}
     WHERE user = {user} AND date IN (
      SELECT date
      FROM users
      ORDER BY date DESC
      LIMIT 1
    )
    '''.format(user=user, feedback=int(feedback)))


def save_reco(user, reco, img, c):
    date = dt.datetime.now().isoformat()
    c.execute('INSERT INTO users VALUES (?,?,?,?,?)',
              (date, user, None, reco, img))


def worker():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    while True:
        data_type, data = reco_queue.get()
        if data_type == 'reco':
            user, reco, img = data
            save_reco(user, reco, img, c)
        else:
            user, feedback = data
            save_feedback(user, feedback, c)
        conn.commit()

    conn.close()


def start_thread():
    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()

if __name__ == '__main__':
    create_table()
