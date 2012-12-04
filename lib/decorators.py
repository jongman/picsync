def memoize(f):
    cache = {}
    def wrapped(*args):
        if args in cache: return cache[args]
        ret = f(*args)
        cache[args] = ret
        return ret

    return wrapped
