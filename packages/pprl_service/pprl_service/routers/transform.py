import string
from typing import TypeVar, Callable

from fastapi import HTTPException, APIRouter
from pprl_core.phonetics_extra import ColognePhonetics
from pprl_core.transform import StringTransformFn, normalize, character_filter, number, date_time, mapping, \
    phonetic_code
from pprl_model import Transformer, NormalizationTransformer, CharacterFilterTransformer, NumberTransformer, \
    DateTimeTransformer, MappingTransformer, AttributeValueEntity, PhoneticCodeAlgorithm, PhoneticCodeTransformer, \
    AnyTransformer, EntityTransformConfig, EmptyValueHandling, EntityTransformRequest, EntityTransformResponse
from pydantic import BaseModel
from pyphonetics import Soundex, Metaphone, RefinedSoundex, FuzzySoundex
from pyphonetics.phonetics import PhoneticAlgorithm
from starlette import status

router = APIRouter()
_M = TypeVar("_M", bound=BaseModel)


def _new_character_filter_transformer(tf: CharacterFilterTransformer):
    return character_filter(tf.characters or str(string.punctuation))


def _new_normalization_transformer(_tf: NormalizationTransformer):
    return normalize()


def _new_number_transformer(tf: NumberTransformer):
    return number(tf.decimal_places)


def _new_date_time_transformer(tf: DateTimeTransformer):
    return date_time(tf.input_format, tf.output_format)


def _new_mapping_transformer(tf: MappingTransformer):
    return mapping(tf.mapping, tf.default_value, tf.inline)


_phonetic_code_mapping: dict[PhoneticCodeAlgorithm, Callable[[], PhoneticAlgorithm]] = {
    PhoneticCodeAlgorithm.soundex: lambda: Soundex(),
    PhoneticCodeAlgorithm.metaphone: lambda: Metaphone(),
    PhoneticCodeAlgorithm.refined_soundex: lambda: RefinedSoundex(),
    PhoneticCodeAlgorithm.fuzzy_soundex: lambda: FuzzySoundex(),
    PhoneticCodeAlgorithm.cologne: lambda: ColognePhonetics()
}


def _new_phonetic_code_transformer(tf: PhoneticCodeTransformer):
    phonetic_alg = _phonetic_code_mapping.get(tf.algorithm)

    if phonetic_alg is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"unimplemented phonetic code algorithm `{phonetic_alg}`"
        )

    return phonetic_code(phonetic_alg())


_transformer_mapping: dict[Transformer, Callable[[_M], StringTransformFn]] = {
    Transformer.character_filter: _new_character_filter_transformer,
    Transformer.normalization: _new_normalization_transformer,
    Transformer.number: _new_number_transformer,
    Transformer.date_time: _new_date_time_transformer,
    Transformer.mapping: _new_mapping_transformer,
    Transformer.phonetic_code: _new_phonetic_code_transformer
}


def _resolve_transformer(tf: AnyTransformer):
    tf_generator_fn = _transformer_mapping.get(tf.name)

    if tf_generator_fn is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"unimplemented transformer `{tf}`"
        )

    return tf_generator_fn(tf)


def _try_transform(
        config: EntityTransformConfig,
        entity: AttributeValueEntity,
        value: str,
        transform_fn: StringTransformFn
):
    empty_value = config.empty_value

    # check if entity is blank
    if value == "":
        if empty_value == EmptyValueHandling.error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"entity with ID `{entity.id}` contains empty field",
            )

        if empty_value == EmptyValueHandling.skip:
            return value

    try:
        return transform_fn(value)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"entity with ID `{entity.id}` could not be processed: {e}",
        )


@router.post("/")
async def preprocess_entities(transform_req: EntityTransformRequest) -> EntityTransformResponse:
    config = transform_req.config
    entities = transform_req.entities
    attribute_transformers = transform_req.attribute_transformers
    global_transformers = transform_req.global_transformers

    attribute_to_transformers_dict: dict[str, list[StringTransformFn]] = {}

    for attribute in attribute_transformers:
        tf_list = [_resolve_transformer(tf) for tf in attribute.transformers]
        attribute_to_transformers_dict[attribute.attribute_name] = tf_list

    global_transformers_before = [_resolve_transformer(tf) for tf in global_transformers.before]
    global_transformers_after = [_resolve_transformer(tf) for tf in global_transformers.after]

    entities_out: list[AttributeValueEntity] = []

    for entity in entities:
        entity_out_attributes: dict[str, str] = {}

        for attr, value in entity.attributes.items():
            for tf in global_transformers_before:
                value = _try_transform(config, entity, value, tf)

            attr_tf = attribute_to_transformers_dict.get(attr)

            if attr_tf is not None:
                for tf in attr_tf:
                    value = _try_transform(config, entity, value, tf)

            for tf in global_transformers_after:
                value = _try_transform(config, entity, value, tf)

            entity_out_attributes[attr] = value

        entities_out.append(AttributeValueEntity(
            id=entity.id,
            attributes=entity_out_attributes,
        ))

    return EntityTransformResponse(
        config=transform_req.config,
        entities=entities_out,
    )
