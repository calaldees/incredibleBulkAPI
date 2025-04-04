# incredibleBulkAPI

* API service for gzip batching of other REST services

---

http://localhost:8000/static_json_gzip/bff-car.json
http://localhost:8000/static_json_gzip/bff-car-images.json

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
        incredible_bulk_api
        image_preview_api

        logs[(/logs/)]
        nginx ..-> logs
        incredible_bulk_api ..-> logs
        image_preview_api ..-> logs

        nginx -- http 8000 --> incredible_bulk_api
        incredible_bulk_api -- http 8001 --> image_preview_api

        %% incredible_bulk_api -- http json--> external
        %% image_preview_api -- http --> external
    end

    subgraph filesystem
        /_static_json_gzip_/[(/static_json_gzip/)]
    end

    /static_json_gzip/ --> nginx
    incredible_bulk_api -- gzip --> /static_json_gzip/
```
