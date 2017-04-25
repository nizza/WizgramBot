import time
import rethinkdb as rdb

from .logs import logger


class FailedToIndexError(Exception):
    pass


def get_chunks(l, n):
    """Chunk a list `l` in chunks of size `n`"""
    for x in range(0, len(l), n):
        yield l[x: x + n]


def safe_index(req, conn,
               retry=5, connection_retry=10):
    """
    Retries to index on failure and reconnects to rethinkdb
    Args:
        chunk (Iterable([BaseData]):
        conn ():
        retry (int): the nb of times to retry
        connection_retry (int): the nb of time to try to reconnect

    Returns:

    """
    def reconnect():
        nonlocal conn
        for i in range(connection_retry):
            try:
                conn = conn.reconnect(noreply_wait=False)
            except (rdb.ReqlDriverError, AttributeError):
                retry_in = i * 2
                logger.warning('Failed to reconnect. '
                               'Retrying in {}sec ({}/{})'.format(
                                retry_in, i, connection_retry))
                time.sleep(retry_in)
            else:
                break
        else:
            raise FailedToIndexError('Could not index the chunk')

    for i in range(retry):
        try:
            resp = rdb.expr(req).run(conn)
        except rdb.ReqlDriverError:
            logger.warning('Reconnecting to rethinkdb ({}/{})'.format(
                i, retry))
            reconnect()
        else:
            break
    else:
        raise FailedToIndexError('Could not index the chunk')

    return resp