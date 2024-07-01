This package implements an HTTP service for PPRL based on Bloom filters.
It covers the preprocessing and masking of records, as well as matching on masked records.
The service is built with [FastAPI](https://fastapi.tiangolo.com/).

# Service endpoints

The service exposes each of the aforementioned steps as an endpoint each.
Their behavior is freely configurable.

## Record preprocessing

`/transform` enables preprocessing of records using a variety of transformers that can be applied to record fields.
These transformers can be applied to all attributes ("globally") or to single attributes.

```python
import httpx

r = httpx.post("http://localhost:8000/transform/", json={
    "config": {
        "empty_value": "error"
    },
    "entities": [
        {
            "id": "001",
            "attributes": {
                "given_name": "John",
                "last_name": "Doe",
                "date_of_birth": "05.06.1978",
                "gender": "male"
            }
        }
    ],
    "global_transformers": {
        "before": [
            {
                "name": "normalization"
            }
        ]
    },
    "attribute_transformers": [
        {
            "attribute_name": "date_of_birth",
            "transformers": [
                {
                    "name": "date_time",
                    "input_format": "%d.%m.%Y",
                    "output_format": "%Y-%m-%d"
                }
            ]
        },
        {
            "attribute_name": "gender",
            "transformers": [
                {
                    "mapping": {
                        "male": "m",
                        "female": "f"
                    },
                    "default_value": "x"
                }
            ]
        }
    ]
})

assert r.status_code == 200

print(r.json()["entities"][0])
# => {'id': '001', 'attributes': {'given_name': 'john', 'last_name': 'doe', 'date_of_birth': '1978-06-05', 'gender': 'm'}}
```

## Record masking

`/mask` enables masking of records based on Bloom filter techniques.
It supports a variety of encoding and hardening methods, as well as control over various bit vector generation
parameters.

```python
import httpx

r = httpx.post("http://localhost:8000/mask/", json={
    "config": {
        "token_size": 2,
        "hash": {
            "function": {
                "algorithms": ["sha1"],
                "key": "s3cr3t_k3y"
            },
            "strategy": {
                "name": "random_hash"
            }
        },
        "filter": {
            "type": "clk",
            "filter_size": 512,
            "hash_values": 5
        },
        "prepend_attribute_name": True,
        "padding": "_",
        "hardeners": [
            {
                "name": "rehash",
                "window_size": 8,
                "window_step": 4,
                "samples": 2
            }
        ]
    },
    "entities": [
        {
            "id": "001",
            "attributes": {
                "given_name": "jon",
                "last_name": "doe",
                "date_of_birth": "1978.06.05",
                "gender": "m"
            }
        }
    ],
    "attributes": [
        {
            "attribute_name": "given_name",
            "salt": {
                "value": "my_s33d"
            }
        }
    ]
})

assert r.status_code == 200
print(r.json()["entities"][0])
# => {'id': '001', 'value': 'RBDAZOkBgFOKMQGGBAJxDSfAQKCAGADyqbB+bQu6cjIkc58MJEgqBbCVgwGCoTSTA6WJA4IDkQEgEQYshQEgLA=='}
```

## Bit vector matching

`/match` enables the computation of similarities between bit vector pairs.
It implements the Dice coefficient, Jaccard index and Cosine similarity as available measures.

```python
import httpx

r = httpx.post("http://localhost:8000/match/", json={
    "config": {
        "measure": "jaccard",
        "threshold": 0.7
    },
    "domain": [
        {
            "id": "D001",
            "value": "RBDAZOkBgFOKMQGGBAJxDSfAQKCAGADyqbB+bQu6cjIkc58MJEgqBbCVgwGCoTSTA6WJA4IDkQEgEQYshQEgLA=="
        },
        {
            "id": "D002",
            "value": "wsJiLptLjVHKvcoMZIR7NS3JaikIMNJiaqRKPOKaZMQEcjsp4ShuEVqSiRU0jTQWB6FIgSKikAAgEW7kpXNMsw=="
        }
    ],
    "range": [
        {
            "id": "R001",
            "value": "AZCMTgvQAUPImaYEaNdzBwXDGHHEDAM+pJH0L5DWdWgUY/4IJkluETLACSGytaDWA7UwhSKSUQBAEIQstQXUXA=="
        },
        {
            "id": "R002",
            "value": "QBBAYOEBgFOKMREGBAZxDSfAQKGEEAJyydB4bQO6dl4gc58EJEgiAZCVgwGCoDSXA6GIA4ODkQEgEAQEhQAgJA=="
        }
    ]
})

assert r.status_code == 200
print(r.json()["matches"])
# => [{'domain': {'id': 'D001', 'value': 'RBDAZOkBgFOKMQGGBAJxDSfAQKCAGADyqbB+bQu6cjIkc58MJEgqBbCVgwGCoTSTA6WJA4IDkQEgEQYshQEgLA=='}, 'range': {'id': 'R002', 'value': 'QBBAYOEBgFOKMREGBAZxDSfAQKGEEAJyydB4bQO6dl4gc58EJEgiAZCVgwGCoDSXA6GIA4ODkQEgEAQEhQAgJA=='}, 'similarity': 0.7771739130434783}]
```

# License

MIT.
