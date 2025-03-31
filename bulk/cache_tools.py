import datetime
import logging
import pickle
import typing as t
import zlib
from functools import wraps
from pathlib import Path

log = logging.getLogger(__name__)


class DoNotPersistCacheException(Exception):
    pass


def default_hash(data) -> str:
    return str(zlib.adler32(data))

def default_args_to_bytes(*args, **kwargs) -> bytes:
    return pickle.dumps((args, kwargs))

def cache_disk(
        original_function: t.Callable | None = None,
        cache_path: Path = Path('__cache'),
        ttl: datetime.timedelta = datetime.timedelta(days=1),
        cache_only=False,
        args_to_bytes_func=default_args_to_bytes,
        hash_function=default_hash,
):
    """
    TODO: doctests with tempfile.tempdir
    """
    cache_path.mkdir(exist_ok=True)

    def _decorate(function):
        @wraps(function)
        async def wrapped_function(*args, **kwargs):
            cache_filename = hash_function(args_to_bytes_func(*args, *kwargs))
            _cache_path = cache_path.joinpath(cache_filename)

            if _cache_path.is_file() and (
                datetime.datetime.fromtimestamp(_cache_path.stat().st_mtime) > datetime.datetime.now() - ttl
            ):
                log.debug(f'loading from cache {args=} {kwargs=}')
                return pickle.load(_cache_path.open(mode='rb'))

            if cache_only:
                log.debug('cache_only - refusing to run original function')
                return

            try:
                _return = await function(*args, **kwargs)  # Wrapped function
            except DoNotPersistCacheException as ex:
                return

            log.debug(f'persisting to cache {args=} {kwargs=}')
            pickle.dump(_return, _cache_path.open(mode='wb'))
            return _return
        return wrapped_function
    # Trick: Allow parenthesised and unparenthesized decorators
    return _decorate(original_function) if callable(original_function) else _decorate
