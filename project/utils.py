
def get_chunks(l, n):
    """Chunk a list `l` in chunks of size `n`"""
    for x in range(0, len(l), n):
        yield l[x: x + n]
