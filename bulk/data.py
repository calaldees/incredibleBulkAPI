import itertools
from typing import Mapping, Sequence


def get_path(data: Sequence | Mapping, path: str | Sequence[str]):
    """
    Utility function to allow safely getting data from nested data structures

    >>> data = {'a': 1, 'b': 2, 'c': [{'d': 4}, 6, {'g': 7}], 'e': 5}

    >>> get_path(data, 'a')
    1
    >>> get_path(data, 'c.0')
    {'d': 4}
    >>> get_path(data, 'c.0.d')
    4
    >>> get_path(data, 'c.0.e')
    >>> get_path(data, 'g')
    >>> get_path(data, 'b.not_real.thing')

    >>> data = [1, 2, {'a':1}]
    >>> get_path(data, '2.a')
    1
    >>> get_path(data, 'a.2')
    """
    _path: list[str] = path.split(".") if isinstance(path, str) else list(path)
    while _path and (key := _path.pop(0)):
        try:
            key = int(key) if isinstance(data, Sequence) else key  # type: ignore[assignment]
            data = data[key]  # type: ignore[call-overload]
        except (IndexError, KeyError, TypeError, ValueError):
            return None
    return data


def crawl_for_key(data: Mapping | Sequence, key):
    """
    >>> data = {'primary_action': 'hello'}
    >>> tuple(crawl_for_key(data, 'primary_action'))
    ('hello',)

    >>> data = [1, 2, {'primary_action': 'hello'}]
    >>> tuple(crawl_for_key(data, 'primary_action'))
    ('hello',)

    >>> data = {'a': 1, 'b': {'primary_action': 'hello'}}
    >>> tuple(crawl_for_key(data, 'primary_action'))
    ('hello',)

    >>> data = {
    ...     'title': 'Live Radio',
    ...     'sections': [
    ...         {
    ...             'content': [
    ...                 {
    ...                     'id': '',
    ...                     'title': '',
    ...                     'type': 'grid',
    ...                     'items': [
    ...                         {
    ...                             'type': 'item',
    ...                             'id': '42Kuap',
    ...                             'image': {
    ...                                 'url': 'fake',
    ...                                 'shape': 'square',
    ...                             },
    ...                             'title': 'The Trial',
    ...                             'primary_action': {
    ...                                 'type': 'navigate',
    ...                                 'payload': {
    ...                                     'link': {
    ...                                         'type': 'item_list',
    ...                                         'href': '/v1/playable_list/42Kuap',
    ...                                     },
    ...                                 },
    ...                             },
    ...                             'enabled': 'true',
    ...                         },
    ...                     ],
    ...                     'primary_action': {
    ...                         'type': 'navigate',
    ...                         'payload': {
    ...                             'link': {
    ...                                 'type': 'item_list',
    ...                                 'href': '/v1/playable_list/2TzewA',
    ...                             },
    ...                         },
    ...                     },
    ...                 }
    ...             ]
    ...         }
    ...     ],
    ... }
    >>> tuple(crawl_for_key(data, 'primary_action'))
    ({'type': 'navigate', 'payload': {'link': {'type': 'item_list', 'href': '/v1/playable_list/2TzewA'}}}, {'type': 'navigate', 'payload': {'link': {'type': 'item_list', 'href': '/v1/playable_list/42Kuap'}}})
    """
    # match type(data):
    #    case Mapping():
    if isinstance(data, Mapping):
        if value := data.get(key):
            yield value
        yield from itertools.chain.from_iterable(
            crawl_for_key(v, key) for k, v in data.items()
        )
    #   case Sequence():
    elif isinstance(data, Sequence) and not isinstance(data, str):
        yield from itertools.chain.from_iterable(crawl_for_key(i, key) for i in data)
    #    case _:
    #        pass
