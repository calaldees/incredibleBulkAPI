# incredibleBulkAPI

* API service for gzip batching REST services


Problems with REST/bff-pattern
------------------------------

* [Backends for Frontends (BFF)](https://learn.microsoft.com/en-us/azure/architecture/patterns/backends-for-frontends) is a powerful design pattern

1. Client performance
    * The UI is performance bound to the round trip time to the backend service.
        * If every a client action triggers a call to bff, this can lead to user interactions being laggy/unresponsive.
    * For mobile clients on less reliable network connections, the bff-pattern can have an even more pronounced impact on performance.
    * In addition to api data returns, clients often perform additional fetches for images. Adding to additional round trip time before a ui could become useable. (some UI may require the images to function)
    * In development/testing of a client, developers often have exceptionally performant network connections. Real life performance of an application can often be hidden from developers.
2. Service outage
    * In the event of a service outage, clients can lock and become unusable for all operations.
3. Service history
    * Most api returns are transitive.
    * If we want to know what an api return looked like yesterday at midday, we have no history or information about this.
    * A service history of API returns could be a useful tool in supporting legacy versions. ("The service worked last week, what's changed in the response?")

Solution
--------

* If the client could prefetch a batch/bulk of some of the hot/frequent data paths, perhaps we could have more responsive applications without the ongoing 'round trip' time.
* Possible client implementation
    * Client operates as normal, fetching data from a bff. In the background the client is fetching the batch/bulk data. (Suggest a max payload of 1MB?)
    * Clients check if a path is in the batch/bulk cache, if not, fetch as normal from bff, else display cached version.
* In addition to providing api data in batches, we can crawl the batch/bulk payloads for images. We can create a second payload with base64-avif encoded previews for placeholder images

### Example

`http://my-site/api/` -> Crawled with `incredibleBulkAPI` once per hour -> `/static_json_gzip/my-site.json.gz`+`/static_json_gzip/my-site.images.json.gz`

#### Example `my-site.json.gz`
```json
{
    "/path": {..., "image_url": "http://examples.com/fake.png"},
    "/path/with/extra/1": {..., "more": [{..., "logo": "logo1.png"},]},
    "/path/with/extra/2": {..., "more": [{..., "logo": "logo2.png"},]},
    "/path/amazing": {...},
    ...
}
```
#### Example `my-site.images.json.gz`
```json
{
    "http://examples.com/fake.png": "data:image/avif;base64,xxx",
    "logo1.png": "data:image/avif;base64,xxx",
    "logo2.png": "data:image/avif;base64,xxx",
}
```


### nginx: `gzip_static on;`

* The linux kernel has a low level operation to take binary content on disk and throws it out of a network socket as a dma transfer operation. This REALLY REALLY fast and handled by hardware.
* All data content is pre-gzipped and served from nginx with `gzip_static on;`
    * The python layer does not serve any data content directly

### Service outage? Single file

* `/fetch?url=xxx&accept=xxx` -> `302` -> `/static_json_gzip/cache/12345.json`
    * If background crawl task has been unable to fetch a new version, the `/static_json_gzip/cache/xxx.json.gz` will still be present as the last received version

### Volumetrics? Examples

* Repeated patterns compress really well
* TODO - numbers



Add a `site` to bulk
--------------------

Each site implements the interface

```python
class AbstractSiteModel:
    endpoint: str
    root_path: APIPath = "/"
    headers: t.Mapping[str, str] = {}
    cache_period: datetime.timedelta

    @abstractmethod
    def extract_crawl_paths(self, path: APIPath, payload: APIPayload) -> t.Iterable[APIPath]:
        ...

    @abstractmethod
    def continue_crawl(self, path: APIPath, depth: APIDepth, payload: APIPayload) -> bool:
        ...


class AbstractImageModel:
    @abstractmethod
    def extract_image_urls(self, data: APIBulk) -> t.Iterable[ImageUrl]:
        ...
```


Architecture
------------

```mermaid
graph TD

    %% external{{external-service}}

    internet{{internet}}
    internet -- http 443 ---> public-server --http 80--> nginx

    subgraph docker-compose [docker-compose]
        nginx
        %% incredible_bulk_api
        image_preview_api

        subgraph incredible_bulk_api [incredible_bulk_api]
            background_fetch
            fetch["/fetch?url="]
        end

        logs[(/logs/)]
        nginx ..-> logs
        incredible_bulk_api ..-> logs
        image_preview_api ..-> logs

        nginx -- http 8000 --> incredible_bulk_api
        background_fetch -- http 8001 --> image_preview_api

    end

    subgraph filesystem ["filesystem /static_json_gzip/"]
        bulk_data[("???.json.gz")]
        bulk_images[("???-images.json.gz")]
        cache_data[("individual cache")]
    end

    filesystem -- gzip_static on; --> nginx
    background_fetch -- .json.gz --> bulk_data
    background_fetch -- .json.gz --> bulk_images

    fetch -- 302 --> cache_data
```


Example Use
-----------

* bulk
    * http://localhost/static_json_gzip/ (auto-index files)
    * data
        * http://localhost/static_json_gzip/bff-car.json (latest) (auto-index shows)
    * images
        * http://localhost/static_json_gzip/bff-car-images.json
            * http://localhost/static/bulk_image_viewer.html?bulk_image_datafile=/static_json_gzip/bff-car-images.json
    * history
        * Every time a bulk payload is created, old versions are renamed and preserved
        * http://localhost/static_json_gzip/bff-car-1970-01-01-00-00.json
        * http://localhost/static_json_gzip/bff-car-images-1970-01-01-00-00.json
* `/fetch` single url (latest)
    * http://localhost/fetch?url=https://bff-car-guacamole.musicradio.com/features&Accept=application/vnd.global.5%2Bjson
    * ```bash
        curl "http://localhost/fetch?url=https://bff-car-guacamole.musicradio.com/features&Accept=application/vnd.global.5%2Bjson" -vvv
        ```
* `/image_preview_api/?url=xxx&width=200` (should probably be hidden for production, but interesting to see)
    * http://localhost/image_preview_api/?url=https://upload.wikimedia.org/wikipedia/commons/e/e4/Redeveloped_Leicester_Square.jpg&width=300


Future
------

* Saving gzip could be a async stream to cloud/edge service?
