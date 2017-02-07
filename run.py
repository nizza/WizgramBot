import argparse
import asyncio
import sqlite3

from project.logs import logger
from project import (UserHandler, start_thread,
                     create_table)

parser = argparse.ArgumentParser('WizGram Bot')
parser.add_argument('--token', required=True)
parser.add_argument('--email', required=True)
parser.add_argument('--password', required=True)


def main(options):
    """

    Args:
        options (dict):

    """
    try:
        create_table()
    except sqlite3.OperationalError:
        logger.warning('Table already exists')

    loop = asyncio.get_event_loop()
    logger.info('Starting thread ...')
    start_thread()

    bot = UserHandler(**options, loop=loop)
    loop.create_task(bot.message_loop())
    logger.info('Listening ...')

    loop.run_forever()

if __name__ == '__main__':
    args = parser.parse_args()
    logger.info('Starting bot')
    main(vars(args))

