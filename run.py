import argparse
import asyncio

from project.logs import logger
from project import UserHandler

parser = argparse.ArgumentParser('WizGram Bot')
parser.add_argument('--token', required=True)
parser.add_argument('--email', required=True)
parser.add_argument('--password', required=True)


def main(options):
    """

    Args:
        options (dict):

    """
    loop = asyncio.get_event_loop()

    bot = UserHandler(**options, loop=loop)
    loop.create_task(bot.message_loop())
    logger.info('Listening ...')

    loop.run_forever()

if __name__ == '__main__':
    args = parser.parse_args()
    logger.info('Starting bot')
    main(vars(args))

