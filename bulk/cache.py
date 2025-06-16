import asyncio
from typing import Awaitable, overload, ParamSpec, TypeVar
from collections.abc import Callable
import logging

from pathlib import Path
import datetime
import dataclasses
import functools


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


@dataclasses.dataclass(frozen=True)
class CachePath():
    path: Path = Path('__cache')
    ttl: datetime.timedelta = datetime.timedelta(minutes=10)
    def __post_init__(self):
        self.path.mkdir(exist_ok=True)


T = TypeVar("T")
P = ParamSpec("P")
def cache_filesystem(
    test: str,
    cache_path: CachePath = CachePath(),
) -> Callable:
    log.info('setup decorator - module level')

    @overload
    def _typed_decorator(fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]: ...
    @overload
    def _typed_decorator(fn: Callable[P, T]) -> Callable[P, T]: ...

    def _typed_decorator(fn: Callable[P, T]) -> Callable:
        #@functools.wraps(fn)
        if asyncio.iscoroutinefunction(fn):
            async def async_decorated(*args: P.args, **kwargs: P.kwargs) -> T:
                logging.info(f'Async {fn.__name__} was called')
                return await fn(*args, **kwargs)
            return async_decorated
        else:
            def sync_decorated(*args: P.args, **kwargs: P.kwargs) -> T:
                logging.info(f'Sync {fn.__name__} was called')
                return fn(*args, **kwargs)
            return sync_decorated
    return _typed_decorator


# def cache_filesystem(
#     test: str,
#     cache_path: CachePath = CachePath(),
# ) -> Callable:
#     log.info('setup decorator - module level')
#     def _typed_decorator[T,**P](fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
#         @functools.wraps(fn)
#         async def decorated(*args: P.args, **kwargs: P.kwargs) -> T:
#             logging.info(f'{fn.__name__} was called')
#             return await fn(*args, **kwargs)
#         return decorated
#     return _typed_decorator



@cache_filesystem('hello')
async def add_two(x: float, y: float) -> float:
    '''Add two numbers together.'''
    log.info('hi')
    return x + y

@cache_filesystem('hello2')
def add_sync(x: float, y: float) -> float:
    return x + y


async def main():
    value = await add_two(1, 2)
    print(value)

if __name__ == "__main__":
    log.info('main')
    asyncio.run(main())
    value = add_sync(3,4)
    print(value)
