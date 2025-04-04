# incredibleBulkAPI

* API service for gzip batching of other REST services

---

http://localhost:8000/static_json_gzip/bff-car.json
http://localhost:8000/static_json_gzip/bff-car-images.json
http://localhost:8000/static/bulk_image_viewer.html?bulk_image_datafile=/static_json_gzip/bff-car-images.json

http://localhost:8000/fetch?url=https://bff-car-guacamole.musicradio.com/features&Accept=application/vnd.global.5%2Bjson

curl "http://localhost:8000/fetch?url=https://bff-car-guacamole.musicradio.com/features&Accept=application/vnd.global.5%2Bjson" -vvv

---

Problems
--------

1. Client performance
2. Service outage
3. Service history

Solution
--------

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
