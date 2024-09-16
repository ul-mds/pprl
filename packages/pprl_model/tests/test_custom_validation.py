import pytest
from pydantic import ValidationError

from pprl_model import EntityTransformRequest, TransformConfig, EmptyValueHandling, AttributeValueEntity, AttributeSalt, \
    RBFFilter, CLKRBFFilter, EntityMaskRequest, MaskConfig, HashConfig, HashFunction, HashAlgorithm, DoubleHash, \
    StaticAttributeConfig, CLKFilter, WeightedAttributeConfig, FilterType


def test_entity_transform_request_no_transformers(uuid4):
    with pytest.raises(ValidationError) as e:
        EntityTransformRequest(
            config=TransformConfig(empty_value=EmptyValueHandling.ignore),
            entities=[
                AttributeValueEntity(
                    id=uuid4(),
                    attributes={
                        "foo": "bar"
                    }
                )
            ],
            attribute_transformers=[]
        )

    assert "attribute and global transformers are empty: must contain at least one" in str(e.value)


def test_attribute_salt_mutually_exclusive():
    with pytest.raises(ValidationError) as e:
        AttributeSalt(
            value="foobar",
            attribute="foobar"
        )

    assert "value and attribute cannot be set at the same time" in str(e.value)


def test_attribute_salt_none_set():
    with pytest.raises(ValidationError) as e:
        AttributeSalt()

    assert "neither value nor attribute is set" in str(e.value)


@pytest.mark.parametrize("filter_type", [
    RBFFilter(hash_values=5, seed=727),
    CLKRBFFilter(hash_values=5)
])
def test_entity_mask_request_static_attribute_with_weighted_filter(filter_type, uuid4):
    with pytest.raises(ValidationError) as e:
        EntityMaskRequest(
            config=MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(
                        algorithms=[HashAlgorithm.sha1],
                        key="foobar"
                    ),
                    strategy=DoubleHash()
                ),
                filter=filter_type
            ),
            entities=[
                AttributeValueEntity(
                    id=uuid4(),
                    attributes={
                        "foo": "bar"
                    }
                )
            ],
            attributes=[
                StaticAttributeConfig(
                    attribute_name="foo",
                    salt=AttributeSalt(value="foobar")
                )
            ]
        )

    assert (f"`{filter_type.type.name}` filters require weighted attribute configurations, "
            f"but static ones were found") in str(e.value)


@pytest.mark.parametrize("filter_type", [
    RBFFilter(hash_values=5, seed=727),
    CLKRBFFilter(hash_values=5)
])
def test_entity_mask_request_no_attributes_with_weighted_filter(filter_type, uuid4):
    with pytest.raises(ValidationError) as e:
        EntityMaskRequest(
            config=MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(
                        algorithms=[HashAlgorithm.sha1],
                        key="foobar"
                    ),
                    strategy=DoubleHash()
                ),
                filter=filter_type
            ),
            entities=[
                AttributeValueEntity(
                    id=uuid4(),
                    attributes={
                        "foo": "bar"
                    }
                )
            ]
        )

    assert (f"`{filter_type.type.name}` filters require weighted attribute configurations, "
            f"but none were found") in str(e.value)


def test_entity_mask_request_weighted_attribute_with_static_filter(uuid4):
    with pytest.raises(ValidationError) as e:
        EntityMaskRequest(
            config=MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(
                        algorithms=[HashAlgorithm.sha1],
                        key="foobar"
                    ),
                    strategy=DoubleHash()
                ),
                filter=CLKFilter(filter_size=128, hash_values=5)
            ),
            entities=[
                AttributeValueEntity(
                    id=uuid4(),
                    attributes={
                        "foo": "bar"
                    }
                )
            ],
            attributes=[
                WeightedAttributeConfig(
                    attribute_name="foo",
                    salt=AttributeSalt(value="foobar"),
                    weight=1,
                    average_token_count=8
                )
            ]
        )

    assert "`clk` filters require static attribute configurations, but weighted ones were found" in str(e.value)


@pytest.mark.parametrize("filter_type", [
    CLKFilter(filter_size=128, hash_values=5),
    RBFFilter(hash_values=5, seed=727),
    CLKRBFFilter(hash_values=5)
])
def test_entity_mask_request_attribute_not_present_on_entity(filter_type, uuid4):
    attr_conf: StaticAttributeConfig | WeightedAttributeConfig
    entity_id = uuid4()

    if filter_type.type == FilterType.clk:
        attr_conf = StaticAttributeConfig(
            attribute_name="###",
            salt=AttributeSalt(value="foobar"),
        )
    else:
        attr_conf = WeightedAttributeConfig(
            attribute_name="###",
            salt=AttributeSalt(value="foobar"),
            weight=1,
            average_token_count=8
        )

    with pytest.raises(ValidationError) as e:
        EntityMaskRequest(
            config=MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(
                        algorithms=[HashAlgorithm.sha1],
                        key="foobar"
                    ),
                    strategy=DoubleHash()
                ),
                filter=filter_type
            ),
            entities=[
                AttributeValueEntity(
                    id=entity_id,
                    attributes={
                        "foo": "bar"
                    }
                )
            ],
            attributes=[attr_conf]
        )

    assert (f"some configured attributes are not present on entities: `###` on "
            f"entities with ID `{entity_id}`") in str(e.value)


@pytest.mark.parametrize("filter_type", [
    CLKFilter(filter_size=128, hash_values=5),
    RBFFilter(hash_values=5, seed=727),
    CLKRBFFilter(hash_values=5)
])
def test_entity_mask_request_attribute_salt_not_present_on_entity(filter_type, uuid4):
    attr_conf: StaticAttributeConfig | WeightedAttributeConfig
    entity_id = uuid4()

    if filter_type.type == FilterType.clk:
        attr_conf = StaticAttributeConfig(
            attribute_name="foo",
            salt=AttributeSalt(attribute="###"),
        )
    else:
        attr_conf = WeightedAttributeConfig(
            attribute_name="foo",
            salt=AttributeSalt(attribute="###"),
            weight=1,
            average_token_count=8
        )

    with pytest.raises(ValidationError) as e:
        EntityMaskRequest(
            config=MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(
                        algorithms=[HashAlgorithm.sha1],
                        key="foobar"
                    ),
                    strategy=DoubleHash()
                ),
                filter=filter_type
            ),
            entities=[
                AttributeValueEntity(
                    id=entity_id,
                    attributes={
                        "foo": "bar"
                    }
                )
            ],
            attributes=[attr_conf]
        )

    assert (f"some configured attribute salts are not present on entities: `###` on "
            f"entities with ID `{entity_id}`") in str(e.value)
