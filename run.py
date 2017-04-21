import argparse
import asyncio

from project.logs import logger
from project import (UserHandler, start_thread)

parser = argparse.ArgumentParser('WizGram Bot')
parser.add_argument('--token', required=True)
parser.add_argument('--email', required=True)
parser.add_argument('--password', required=True)

parser.add_argument('--host', default='localhost', help='Host for rethinkdb')
parser.add_argument('--port', default=28015, help='Port for rethinkdb')
parser.add_argument('--db', default='bots', help='Database for rethinkdb')


def main(options):
    """

    Args:
        options (dict):

    """

    loop = asyncio.get_event_loop()

    logger.info('Starting thread ...')
    start_thread(**options)

    bot = UserHandler(**options, loop=loop)
    loop.create_task(bot.message_loop())
    logger.info('Listening ...')

    loop.run_forever()

if __name__ == '__main__':
    args = parser.parse_args()
    logger.info('Starting bot')
    main(vars(args))

