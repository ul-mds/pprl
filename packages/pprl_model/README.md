This package contains model classes that are used in the PPRL service for validation purposes.
They have been conceived with the idea of an HTTP-based service for record linkage based on Bloom filters in mind.
It encompasses models for the service's data transformation, masking and bit vector matching routines.
[Pydantic](https://docs.pydantic.dev/latest/) is used for validation, serialization and deserialization.
This package is rarely to be used directly.
Instead, it is used by other packages to power their functionalities.

# Data models

Models for entity pre-processing, masking and bit vector matching are exposed through this package.
The following examples are taken from the test suites of the
[PPRL service package](https://github.com/ul-mds/pprl/tree/main/packages/pprl_service) and show additional
validation steps in addition to the ones native to Pydantic.

## Entity transformation

```python
from pprl_model import EntityTransformRequest, TransformConfig, EmptyValueHandling, AttributeValueEntity, \
    AttributeTransformerConfig, NumberTransformer, GlobalTransformerConfig, NormalizationTransformer, \
    CharacterFilterTransformer

# This is a valid config.
_ = EntityTransformRequest(
    config=TransformConfig(empty_value=EmptyValueHandling.ignore),
    entities=[
        AttributeValueEntity(
            id="001",
            attributes={
                "bar1": "  12.345  ",
                "bar2": "  12.345  "
            }
        )
    ],
    attribute_transformers=[
        AttributeTransformerConfig(
            attribute_name="bar1",
            transformers=[
                NumberTransformer(decimal_places=2)
            ]
        )
    ],
    global_transformers=GlobalTransformerConfig(
        before=[
            NormalizationTransformer()
        ],
        after=[
            CharacterFilterTransformer(characters=".")
        ]
    )
)

from uuid import uuid4

# Validation will fail since no transformers have been defined.
_ = EntityTransformRequest(
    config=TransformConfig(empty_value=EmptyValueHandling.ignore),
    entities=[
        AttributeValueEntity(
            id=str(uuid4()),
            attributes={
                "foo": "bar"
            }
        )
    ],
    attribute_transformers=[]
)
# => ValidationError: attribute and global transformers are empty: must contain at least one
```

## Entity masking

```python
from pprl_model import EntityMaskRequest, MaskConfig, HashConfig, HashFunction, HashAlgorithm, \
    DoubleHash, CLKFilter, AttributeValueEntity, StaticAttributeConfig, AttributeSalt, CLKRBFFilter

# This is a valid config.
_ = EntityMaskRequest(
    config=MaskConfig(
        token_size=2,
        hash=HashConfig(
            function=HashFunction(algorithms=[HashAlgorithm.sha1]),
            strategy=DoubleHash()
        ),
        filter=CLKFilter(filter_size=1024, hash_values=5),
        padding="_"
    ),
    entities=[
        AttributeValueEntity(
            id="001",
            attributes={
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1987-06-05",
                "gender": "m"
            }
        )
    ]
)

# This is an invalid config since salting an attribute can only be done through a fixed value
# or another attribute on an entity, not both at the same time.
_ = EntityMaskRequest(
    config=MaskConfig(
        token_size=2,
        hash=HashConfig(
            function=HashFunction(algorithms=[HashAlgorithm.sha1]),
            strategy=DoubleHash()
        ),
        filter=CLKFilter(filter_size=1024, hash_values=5),
        padding="_"
    ),
    entities=[
        AttributeValueEntity(
            id="001",
            attributes={
                "first_name": "foobar",
                "salt": "0123456789"
            }
        )
    ],
    attributes=[
        StaticAttributeConfig(
            attribute_name="first_name",
            salt=AttributeSalt(
                value="my_salt",
                attribute="salt"
            )
        )
    ]
)
# => ValidationError: value and attribute cannot be set at the same time

# This also fails if neither a static value nor an attribute are set for salting.
_ = EntityMaskRequest(
    config=MaskConfig(
        token_size=2,
        hash=HashConfig(
            function=HashFunction(algorithms=[HashAlgorithm.sha1]),
            strategy=DoubleHash()
        ),
        filter=CLKFilter(filter_size=1024, hash_values=5),
        padding="_"
    ),
    entities=[
        AttributeValueEntity(
            id="001",
            attributes={
                "first_name": "foobar",
                "salt": "0123456789"
            }
        )
    ],
    attributes=[
        StaticAttributeConfig(
            attribute_name="first_name",
            salt=AttributeSalt()
        )
    ]
)
# => ValidationError: neither value nor attribute is set

# When using a weighted filter (RBF, CLKRBF), an error will be thrown if any attribute configuration 
# provided is static, not weighted. The same applies vice versa, meaning if CLK is specified as a filter and
# weighted attribute configurations are provided.
_ = EntityMaskRequest(
    config=MaskConfig(
        token_size=2,
        hash=HashConfig(
            function=HashFunction(algorithms=[HashAlgorithm.sha1]),
            strategy=DoubleHash()
        ),
        filter=CLKRBFFilter(hash_values=5),
        padding="_"
    ),
    entities=[
        AttributeValueEntity(
            id="001",
            attributes={
                "first_name": "foobar",
                "salt": "0123456789"
            }
        )
    ],
    attributes=[
        StaticAttributeConfig(
            attribute_name="first_name",
            salt=AttributeSalt(value="my_salt")
        )
    ]
)
# => ValidationError: `clkrbf` filters require weighted attribute configurations, but static ones were found

# Weighted filters (RBF, CLKRBF) always require weighted attribute configurations. If none
# are provided, validation fails.
_ = EntityMaskRequest(
    config=MaskConfig(
        token_size=2,
        hash=HashConfig(
            function=HashFunction(algorithms=[HashAlgorithm.sha1]),
            strategy=DoubleHash()
        ),
        filter=CLKRBFFilter(hash_values=5),
        padding="_"
    ),
    entities=[
        AttributeValueEntity(
            id="001",
            attributes={
                "first_name": "foobar",
                "salt": "0123456789"
            }
        )
    ]
)
# => ValidationError: `clkrbf` filters require weighted attribute configurations, but none were found

# If a configuration is provided for an attribute that doesn't exist on some entities, validation fails.
_ = EntityMaskRequest(
    config=MaskConfig(
        token_size=2,
        hash=HashConfig(
            function=HashFunction(algorithms=[HashAlgorithm.sha1]),
            strategy=DoubleHash()
        ),
        filter=CLKFilter(filter_size=1024, hash_values=5),
        padding="_"
    ),
    entities=[
        AttributeValueEntity(
            id="001",
            attributes={
                "first_name": "foobar"
            }
        )
    ],
    attributes=[
        StaticAttributeConfig(
            attribute_name="last_name",
            salt=AttributeSalt(value="my_salt")
        )
    ]
)
# => ValidationError: some configured attributes are not present on entities: `last_name` on entities with ID `001`
```

## Bit vector matching

```python
from pprl_model import VectorMatchRequest, MatchConfig, SimilarityMeasure, BitVectorEntity

_ = VectorMatchRequest(
    config=MatchConfig(
        measure=SimilarityMeasure.jaccard,
        threshold=0.8
    ),
    domain=[
        BitVectorEntity(
            id="D001",
            value="kY7yXn+rmp8L0nyGw5NlMw=="
        )
    ],
    range=[
        BitVectorEntity(
            id="R001",
            value="qig0C1i8YttqhPwo4VqLlg=="
        )
    ]
)
```

# License

MIT.
