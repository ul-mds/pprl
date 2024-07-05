This package contains a small HTTP-based library for working with the server provided by
the [PPRL service package](https://github.com/ul-mds/pprl/tree/main/packages/pprl_service).
It also contains a command-line application which uses the library to process CSV files.

# Library methods

The library exposes functions for entity pre-processing, masking and bit vector matching.
They follow the data model that is also used by the PPRL service, which is exposed through
the [PPRL model package](https://github.com/ul-mds/pprl/tree/main/packages/pprl_model).

In addition to the request objects, each function accepts a base URL, a full URL and a connection timeout in seconds as
optional parameters.
By default, the base URL is set to http://localhost:8000.
The full URL, if set, takes precedence over the base URL.
The connection timeout is set to 10 seconds by default, but should be increased for large-scale requests.

## Entity transformation

```python
import pprl_client
from pprl_model import EntityTransformRequest, EntityTransformConfig, EmptyValueHandling, AttributeValueEntity, \
    GlobalTransformerConfig, NormalizationTransformer

response = pprl_client.transform(EntityTransformRequest(
    config=EntityTransformConfig(empty_value=EmptyValueHandling.error),
    entities=[
        AttributeValueEntity(
            id="001",
            attributes={
                "first_name": "Müller",
                "last_name": "Ludenscheidt"
            }
        )
    ],
    global_transformers=GlobalTransformerConfig(
        before=[NormalizationTransformer()]
    )
))

print(response.entities)
# => [AttributeValueEntity(id='001', attributes={'first_name': 'muller', 'last_name': 'ludenscheidt'})]
```

## Entity masking

```python
import pprl_client
from pprl_model import EntityMaskRequest, MaskConfig, HashConfig, HashFunction, HashAlgorithm, RandomHash, CLKFilter, \
    AttributeValueEntity

response = pprl_client.mask(EntityMaskRequest(
    config=MaskConfig(
        token_size=2,
        hash=HashConfig(
            function=HashFunction(
                algorithms=[HashAlgorithm.sha1],
                key="s3cr3t_k3y"
            ),
            strategy=RandomHash()
        ),
        filter=CLKFilter(hash_values=5, filter_size=256)
    ),
    entities=[
        AttributeValueEntity(
            id="001",
            attributes={
                "first_name": "muller",
                "last_name": "ludenscheidt"
            }
        )
    ]
))

print(response.entities)
# => [BitVectorEntity(id='001', value='SKkgqBHBCJJCANICEKSpWMAUBYCQEMLuZgEQGBKRC8A=')]
```

## Bit vector matching

```python
import pprl_client
from pprl_model import MatchRequest, MatchConfig, SimilarityMeasure, BitVectorEntity

response = pprl_client.match(MatchRequest(
    config=MatchConfig(
        measure=SimilarityMeasure.jaccard,
        threshold=0.8
    ),
    domain=[
        BitVectorEntity(
            id="001",
            value="SKkgqBHBCJJCANICEKSpWMAUBYCQEMLuZgEQGBKRC8A="
        )
    ],
    range=[
        BitVectorEntity(
            id="100",
            value="UKkgqBHBDJJCANICELSpWMAUBYCMEMLrZgEQGBKRC7A="
        ),
        BitVectorEntity(
            id="101",
            value="H5DN45iUeEjrjbHZrzHb3AyQk9O4IgxcpENKKzEKRLE="
        )
    ]
))

print(response.matches)
# => [Match(domain=BitVectorEntity(id='001', value='SKkgqBHBCJJCANICEKSpWMAUBYCQEMLuZgEQGBKRC8A='), range=BitVectorEntity(id='100', value='UKkgqBHBDJJCANICELSpWMAUBYCMEMLrZgEQGBKRC7A='), similarity=0.8536585365853658)]
```

# Command line interface

The `pprl` command exposes all the library's functions and adapts them to work with CSV files. 
Running `pprl --help` provides an overview of the command options.

```
$ pprl --help
Usage: pprl [OPTIONS] COMMAND [ARGS]...

  HTTP client for performing PPRL based on Bloom filters.

Options:
  --base-url TEXT                 base URL to HTTP-based PPRL service
  -b, --batch-size INTEGER RANGE  amount of bit vectors to match at a time  [x>=1]
  --timeout-secs INTEGER RANGE    seconds until a request times out  [x>=1]
  --delimiter TEXT                column delimiter for CSV files
  --encoding TEXT                 character encoding for files
  --help                          Show this message and exit.

Commands:
  mask       Mask a CSV file with entities.
  match      Match bit vectors from CSV files against each other.
  transform  Perform pre-processing on a CSV file with entities.
```

`pprl mask` has separate subcommands for each supported filter type.

```
$ pprl mask --help
Usage: pprl mask [OPTIONS] COMMAND [ARGS]...

  Mask a CSV file with entities.

Options:
  --help  Show this message and exit.

Commands:
  clk     Mask a CSV file with entities using a CLK filter.
  clkrbf  Mask a CSV file with entities using a CLKRBF filter.
  rbf     Mask a CSV file with entities using an RBF filter.
```

The `pprl` command works on two basic types of CSV files that follow a simple structure.
Entity files are CSV files that contain a column with a unique identifier and arbitrary additional columns which
contain values for certain attributes that identify an entity.
Each row is representative of a single entity.

```csv
id,first_name,last_name,date_of_birth,gender
001,Natalie,Sampson,1956-12-16,female
002,Eric,Lynch,1910-01-11,female
003,Pam,Vaughn,1983-10-05,male
004,David,Jackson,2006-01-27,male
005,Rachel,Dyer,1904-02-02,female
```

Bit vector files contain an ID column and a value column which contains a representative bit vector.
These bit vectors are generally generated by masking a record from an entity file.

```csv
id,value
001,0Dr8t+kE5ltI+xdM85fwx0QLrTIgvFN35/0YvODNdOE0AaUHPphikXYy4LlArE4UqfjPs+wKtT233R7lBzSp5mwkCjTzA1tl0N7s+sFeKyIrOiGk0gNIYvA=
002,QMEIkE9TN1Quv0K0QAIk1RZD3qF7nQh0IyOYqVDf8IQkyaLGcFjiLHsEgBpU8CRSCuATbWpjEwGi3dilizySQy4miGiJolilYmwKysjseq+IFsAU3T1IRjA=
003,BqFoNZhrAVBq9SV1wBK0dUZLHDM9hCBoO4XdKCzvasSUELQeAB8+DV5tAhDl5KCSJfDCB6JG4WSoCFbozXqBYSUMqEQJE0JwhpRK6oLOcRRoGwGESDBMZwA=
004,8C9KItMTwtz4oXQvo8G0t1bTnwspnghmJwyqqcL2RIHASb4XJHAqybMCXQBm5mq6h/kdxGbblxBjhy79jRUcI60haqZhNsst0n7OUAxM/UoZVumIilRIbCA=
005,CFk4I0sKwnRoiTEOQASy1QZfHCGB1GBgYQDcZwDDtIkGGLOmLRhrQyOSlQDUDoYTbvaBRVqbkRnqmYQbDTEGlG+2y60FMmBEKtxsr0I4I00oMpuoXAsDWmA=
```

Pre-processing is done with the `pprl transform` command.
It requires an entity file and an output file to write the pre-processed entities to.
Attribute and global transformer configurations can be provided, but at least one must be specified.

In this example, a global normalization transformer which is executed before all other attribute-specific transformers
is defined.
Date time reformatting is applied to the "date of birth" column in the input file.

_attribute.json_

```json
[
  {
    "attribute_name": "date_of_birth",
    "transformers": [
      {
        "name": "date_time",
        "input_format": "%Y-%m-%d",
        "output_format": "%Y%m%d"
      }
    ]
  }
]
```

_global.json_

```json
{
  "before": [
    {
      "name": "normalization"
    }
  ]
}
```

```
$ pprl transform ./input.csv ./output.csv --attribute-config-path ./attribute.json --global-config-path ./global.json 
Transforming entities  [####################################]  100%
```

_output.csv_

```csv
id,first_name,last_name,date_of_birth,gender
001,natalie,sampson,19561216,female
002,eric,lynch,19100111,female
003,pam,vaughn,19831005,male
004,david,jackson,20060127,male
005,rachel,dyer,19040202,female
```

Masking is done with `pprl mask` and its subcommands.
Depending on the filter type, `clk`, `rbf` or `clkrbf` must be specified.
The required arguments depend on the selected filter type.
All filter types expect an entity file and an output file to write the masked entities to.
Additionally:

- `pprl mask clk` requires a filter size in bits and an amount of hash values to generate per token
- `pprl mask rbf` requires a minimum amount of hash values to generate per token and a seed for the sampling of bits 
  for the resulting bit vector
- `pprl mask clkrbf` requires a minimum amount of hash values to generate per token

In this example, entities are masked using a CLK filter with a size of 512 bits and five hash values per token.
Attribute values are split into tokens of size two.
The random hashing scheme is applied and the key "s3cr3t_k3y" is applied to the default hash function SHA256 to make
it a keyed hash function.
After masking, bit vectors are hardened by randomly shuffling their bits and rehashing them.

_input.csv_

```csv
id,first_name,last_name,date_of_birth,gender
001,natalie,sampson,19561216,female
002,eric,lynch,19100111,female
003,pam,vaughn,19831005,male
004,david,jackson,20060127,male
005,rachel,dyer,19040202,female
```

_hardener.json_

```json
[
  {
    "name": "permute",
    "seed": 727
  },
  {
    "name": "rehash",
    "window_size": 16,
    "window_step": 8,
    "samples": 2
  }
]
```

```
$ pprl mask clk ./input.csv ./output.csv 512 5 -q 2 -s s3cr3t_k3y --hash-strategy random_hash --hardener-config-path ./hardener.json
Masking entities  [####################################]  100%
```

_output.csv_

```csv
id,value
001,wAWgITvQ1/VACpRYC2EKrfCkWziyEhmyKwi5sMsFrAQVoIBygTQScPRoIIAto0AwS0ihlcAIFAcQRwccY5IOmQ==
002,cFCwQIABQ+TgSSdlGM/z54BEUgmYhA1GKtCxQAKAXFIWiPAFIQYaFArgM61pUAAeATwBlBEOEw4Oowe0rbcMGw==
003,IgK16AAISCRoCuVAb1UBZYBBhGgxSEkKeMkTUCKAx4IAsNGJBS4ShgBAGIapBIQWJLiBFEEKAIWAGYS8ZZGMKw==
004,ZlBkyoYIEWmeaxbPDNng5JjHACkCAJwjlBCJQBJ4ZBSyOAukACUahOAFQ20oNwTQEDRA005+VUUfsUQcKCGNxg==
005,cUekQFQkI7TpTcRwmcNDoodRRBshlSEiAUjBQiMlxBLTmODMJICmDmxgUqYKonQEMFD58QsogRQFIgYUwJDOHA==
```

Matching is done with the `pprl match` command.
It allows the matching of multiple bit vector input files at once.
If more than two files are provided, the command will pick out pairs of files and matches their contents against one 
another.

In this example, the bit vectors of two files are matched against each other.
The Jaccard index is used as a similarity measure and a match threshold of 70% is applied.

_domain.csv_

```csv
id,value
001,wAWgITvQ1/VACpRYC2EKrfCkWziyEhmyKwi5sMsFrAQVoIBygTQScPRoIIAto0AwS0ihlcAIFAcQRwccY5IOmQ==
002,cFCwQIABQ+TgSSdlGM/z54BEUgmYhA1GKtCxQAKAXFIWiPAFIQYaFArgM61pUAAeATwBlBEOEw4Oowe0rbcMGw==
003,IgK16AAISCRoCuVAb1UBZYBBhGgxSEkKeMkTUCKAx4IAsNGJBS4ShgBAGIapBIQWJLiBFEEKAIWAGYS8ZZGMKw==
004,ZlBkyoYIEWmeaxbPDNng5JjHACkCAJwjlBCJQBJ4ZBSyOAukACUahOAFQ20oNwTQEDRA005+VUUfsUQcKCGNxg==
005,cUekQFQkI7TpTcRwmcNDoodRRBshlSEiAUjBQiMlxBLTmODMJICmDmxgUqYKonQEMFD58QsogRQFIgYUwJDOHA==
```

_range.csv_

```csv
id,value
101,kUSyxIgtIDSAB7ZYDkFQRZpFoMkCjCCCbDTWAUJTRAAEBpspBX4PNUZKi1AIVCABAjg6EAoKuwVleeUYgRBYoQ==
102,IAA0YE4MGexIiYdEjwNzoOKmIA4CEHEiKQASYFPhxQTQlPAAgYW3AWBYmQJ8YMoaAj0ZkoOrFyUmFo52TDcIKw==
103,BFAwREkkQbTdzddgDHFWgMRJMyxAMW+jq2ASICMBtIEr+YDCBRUgxEDIsQpciO4mAK3h2cIbXFQCMlaVpJPZIQ==
104,wBWgITvQ2/VACpRYC2EKrfCkWxiyEhmyKwi5sMsFrBQVoIBygTQScPRoIIAto0AwS0ihldAIFAcQRwccY5IOmQ==
105,QCCwIKQAED5AjaZYmodDcZAEBKkIxgAiDfEUoDKEdgEAEJAMAwcfQEbQkaQ4ANAABqiUscAKPQZEMJxRhTGIGQ==
```

```
$ pprl match domain.csv range.csv output.csv -m jaccard -t 0.7
Matching bit vectors from domain.csv and range.csv  [####################################]  100%
```

_output.csv_

```csv
domain_id,domain_file,range_id,range_file,similarity
001,domain.csv,104,range.csv,0.9690721649484536
```

# License

MIT.
