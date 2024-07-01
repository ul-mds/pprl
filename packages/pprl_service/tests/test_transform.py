from pprl_model import EntityTransformRequest, EntityTransformConfig, EmptyValueHandling, AttributeValueEntity, \
    CharacterFilterTransformer, AttributeTransformerConfig, EntityTransformResponse, DateTimeTransformer, \
    MappingTransformer, NormalizationTransformer, NumberTransformer, PhoneticCodeTransformer, GlobalTransformerConfig, \
    PhoneticCodeAlgorithm
from starlette import status


def test_character_filter(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.ignore),
        entities=[AttributeValueEntity(id="001", attributes={"foo": "bar$"})],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="foo",
                transformers=[CharacterFilterTransformer(characters="$")],
            )
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_200_OK

    tf_resp = EntityTransformResponse(**r.json())

    assert tf_resp.config == tf_req.config
    assert tf_resp.entities == [
        AttributeValueEntity(id="001", attributes={"foo": "bar"})
    ]


def test_date_time(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.ignore),
        entities=[AttributeValueEntity(id="001", attributes={"foo": "29.06.1998"})],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="foo",
                transformers=[
                    DateTimeTransformer(input_format="%d.%m.%Y", output_format="%Y-%m-%d")
                ],
            )
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_200_OK

    tf_resp = EntityTransformResponse(**r.json())

    assert tf_resp.config == tf_req.config
    assert tf_resp.entities == [
        AttributeValueEntity(id="001", attributes={"foo": "1998-06-29"})
    ]


def test_mapping(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.ignore),
        entities=[AttributeValueEntity(id="001", attributes={"foo": "bar"})],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="foo",
                transformers=[MappingTransformer(mapping={"bar": "baz"})],
            )
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_200_OK

    tf_resp = EntityTransformResponse(**r.json())

    assert tf_resp.config == tf_req.config
    assert tf_resp.entities == [
        AttributeValueEntity(id="001", attributes={"foo": "baz"})
    ]


def test_mapping_with_default(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.ignore),
        entities=[AttributeValueEntity(id="001", attributes={"foo": "bar"})],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="foo",
                transformers=[
                    MappingTransformer(mapping={"x": "y"}, default_value="baz")
                ],
            )
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_200_OK

    tf_resp = EntityTransformResponse(**r.json())

    assert tf_resp.config == tf_req.config
    assert tf_resp.entities == [
        AttributeValueEntity(id="001", attributes={"foo": "baz"})
    ]


def test_mapping_with_inline(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.ignore),
        entities=[AttributeValueEntity(id="001", attributes={"foo": "bar"})],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="foo",
                transformers=[MappingTransformer(mapping={"r": "z"}, inline=True)],
            )
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_200_OK

    tf_resp = EntityTransformResponse(**r.json())

    assert tf_resp.config == tf_req.config
    assert tf_resp.entities == [
        AttributeValueEntity(id="001", attributes={"foo": "baz"})
    ]


def test_normalize(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.ignore),
        entities=[AttributeValueEntity(id="001", attributes={"foo": "  b  ár "})],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="foo", transformers=[NormalizationTransformer()]
            )
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_200_OK

    tf_resp = EntityTransformResponse(**r.json())

    assert tf_resp.config == tf_req.config
    assert tf_resp.entities == [
        AttributeValueEntity(id="001", attributes={"foo": "b ar"})
    ]


def test_number(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.ignore),
        entities=[
            AttributeValueEntity(
                id="001", attributes={"bar1": "0012.345", "bar2": "0012.345"}
            )
        ],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="bar1",
                transformers=[NumberTransformer(decimal_places=0)],
            ),
            AttributeTransformerConfig(
                attribute_name="bar2",
                transformers=[NumberTransformer(decimal_places=2)],
            ),
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_200_OK

    tf_resp = EntityTransformResponse(**r.json())

    assert tf_resp.config == tf_req.config
    assert tf_resp.entities == [
        AttributeValueEntity(id="001", attributes={"bar1": "12", "bar2": "12.35"})
    ]


def test_phonetic(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.ignore),
        entities=[AttributeValueEntity(id="001", attributes={"foo": "bar"})],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="foo",
                transformers=[
                    PhoneticCodeTransformer(algorithm=PhoneticCodeAlgorithm.soundex)
                ],
            )
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_200_OK

    tf_resp = EntityTransformResponse(**r.json())

    assert tf_resp.config == tf_req.config
    assert tf_resp.entities == [
        AttributeValueEntity(id="001", attributes={"foo": "B600"})
    ]


def test_global_transformers(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.ignore),
        entities=[
            AttributeValueEntity(
                id="001", attributes={"bar1": "  12.345  ", "bar2": "  12.345  "}
            )
        ],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="bar1",
                transformers=[NumberTransformer(decimal_places=2)],
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

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_200_OK

    tf_resp = EntityTransformResponse(**r.json())

    assert tf_resp.config == tf_req.config
    assert tf_resp.entities == [
        AttributeValueEntity(id="001", attributes={"bar1": "1235", "bar2": "12345"})
    ]


def test_ignore_on_empty_values(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.ignore),
        entities=[AttributeValueEntity(id="001", attributes={"foo": ""})],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="foo",
                transformers=[
                    DateTimeTransformer(input_format="%d.%m.%Y", output_format="%Y-%m-%d")
                ],
            )
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "entity with ID `001` could not be processed" in r.json()["detail"]


def test_skip_on_empty_values(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.skip),
        entities=[AttributeValueEntity(id="001", attributes={"foo": ""})],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="foo",
                transformers=[
                    DateTimeTransformer(input_format="%d.%m.%Y", output_format="%Y-%m-%d")
                ],
            )
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_200_OK

    tf_resp = EntityTransformResponse(**r.json())

    assert tf_resp.config == tf_req.config
    assert tf_resp.entities == [AttributeValueEntity(id="001", attributes={"foo": ""})]


def test_error_on_empty_values(test_client):
    tf_req = EntityTransformRequest(
        config=EntityTransformConfig(empty_value=EmptyValueHandling.error),
        entities=[AttributeValueEntity(id="001", attributes={"foo": ""})],
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="foo",
                transformers=[
                    DateTimeTransformer(input_format="%d.%m.%Y", output_format="%Y-%m-%d")
                ],
            )
        ],
    )

    r = test_client.post("/transform", json=tf_req.model_dump())

    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "entity with ID `001` contains empty field" in r.json()["detail"]
