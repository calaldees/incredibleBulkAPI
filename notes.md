```python
import aiohttp

    async with aiohttp.ClientSession() as session:
        # breakpoint()   # i can get to here
        async with session.request(
            method=method,
            url=url,
            headers=headers,
            timeout=5,
            ssl=False,  # Ignore all SSL certificates
        ) as response:
            breakpoint()  # I cant get to here!? .. wtf?
            if response.status_code != 200:
                log.warning(f"Failed {url=}")
                raise DoNotPersistCacheException(f"failed: {url}")
            return await response.json()

```

```python
from gzip_stream import GZIPCompressedStream
with open('my_very_big_1tb_file.txt') as file_to_upload:
    compressed_stream = GZIPCompressedStream(
        file_to_upload,
        compression_level=7
    )
    upload_client.upload_fileobj(compressed_stream)
```