from __future__ import annotations

import logging
import typing as t
from abc import abstractmethod

import ujson as json

from .fetch import fetch_url
from .site_model import APIBulk

log = logging.getLogger(__name__)


type ImageUrl = str
type Base64EncodedImage = str
type FetchImageBase64Callable = t.Callable[[ImageUrl], t.Awaitable[Base64EncodedImage]]
type APIBulkImages = t.Mapping[ImageUrl, Base64EncodedImage]


def progress_debug(iterable: t.Iterable):
    count = 0
    for i in iterable:
        count += 1
        if count % 100 == 0:
            log.debug('image count {}', count)
        yield i


class AbstractImageModel:
    fetch_image_preview_base64: FetchImageBase64Callable

    async def image_previews(self, api_bulk: APIBulk) -> APIBulkImages:
        return {
            image_url: await self.fetch_image_preview_base64(image_url)
            for image_url in self.extract_image_urls(api_bulk)
        }

    @abstractmethod
    def extract_image_urls(self, data: APIBulk) -> t.Iterable[ImageUrl]:
        """
        Identify all image urls to create previews of
        """
        ...
