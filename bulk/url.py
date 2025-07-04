from collections.abc import Mapping
from urllib.parse import urlencode, urlparse, urlunparse


def compose_url(
    urlstring: str = '',
    scheme: str = '',
    netloc: str = '',
    host: str = '',
    port: int = 0,
    path: str = '',
    params: str = '',
    query: str | Mapping[str, str] = '',
    fragment: str = '',
) -> str:
    """
    Utility for combining `urlparse` with overlaying parts of the url

    For url_part index's - refer to https://docs.python.org/3.14/library/urllib.parse.html#urllib.parse.urlparse
    scheme://netloc/path;parameters?query#fragment

    >>> compose_url('myhostname')
    'http://localhost/myhostname'
    >>> compose_url(host='myhostname')
    'http://myhostname/'
    >>> compose_url(host='myhostname', port=8000)
    'http://myhostname:8000/'
    >>> compose_url(host='myhostname', port=8000, query={'a': 1, 'b': 2})
    'http://myhostname:8000/?a=1&b=2'
    >>> compose_url(urlstring='https://drive.google.com/files')
    'https://drive.google.com/files'
    >>> compose_url(urlstring='https://drive.google.com/files', path='/alternate/files')
    'https://drive.google.com/alternate/files'
    """
    return urlunparse(
        kwarg_value or baseurl_value or fallback_value
        for kwarg_value, baseurl_value, fallback_value in zip(
            (
                scheme,
                netloc if netloc else host + (f':{port}' if port else ''),
                path,
                params,
                urlencode(query) if isinstance(query, Mapping) else query,
                fragment,
            ),
            urlparse(urlstring),
            (
                'http',  # scheme
                'localhost',  # netloc
                '/',  # path
                '',  # params
                '',  # query
                '',  # fragment
            ),
        )
    )
