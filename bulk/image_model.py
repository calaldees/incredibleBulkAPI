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
type APIBulkImages = t.Mapping[ImageUrl, Base64EncodedImage]


IMAGE_PREVIEW_SERVICE = "http://image_preview_api:8000"


def progress_debug(iterable: t.Iterable):
    count = 0
    for i in iterable:
        count += 1
        if count % 100 == 0:
            log.debug('image count {}', count)
        yield i



class AbstractImageModel:

    async def image_previews(self, api_bulk: APIBulk) -> APIBulkImages:
        return {
            image_url: await self.get_image_preview_avif_base64(image_url)
            for image_url in self.extract_image_urls(api_bulk)
        }

    async def get_image_preview_avif_base64(self, image_url: ImageUrl) -> Base64EncodedImage:
        log.info(f"fetch image preview for {image_url[-8:]}")
        try:
            return (
                (
                    await fetch_url(
                        method="POST",
                        url=image_url,
                        data=json.dumps({"url": image_url}),
                        headers={"Content-Type": "application/json"},
                    )
                )
                .decode("utf8")
            )
            # response = await client.post(IMAGE_PREVIEW_SERVICE,json={'url': image_url})
            # if response and response.status_code == 200:
            #   return response.text
        except Exception as ex:
            log.exception(ex)
        return ""

    @abstractmethod
    def extract_image_urls(self, data: APIBulk) -> t.Iterable[ImageUrl]:
        """
        Identify all image urls to create previews of
        """
        ...
