import time, functools

def retry(exceptions, tries=3, delay=1, backoff=2):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            mdelay = delay
            for attempt in range(tries):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    if attempt == tries - 1:
                        raise
                    time.sleep(mdelay)
                    mdelay *= backoff
        return wrapper
    return decorator
