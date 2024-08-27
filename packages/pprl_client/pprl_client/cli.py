import copy
import csv
import itertools
import json
from pathlib import Path
from typing import Any, TypeVar, Type, Callable

import click
from pprl_model import BitVectorEntity, TransformConfig, AttributeValueEntity, \
    GlobalTransformerConfig, WeightedAttributeConfig, BaseTransformRequest, \
    NormalizationTransformer, EmptyValueHandling, BaseMaskRequest, BaseMatchRequest
from pydantic import BaseModel

from pprl_client import lib
from pprl_client.model import FakerGeneratorConfig, GeckoGeneratorConfig, FakerGeneratorSpec

_M = TypeVar("_M", bound=BaseModel)


def _maybe_read_json(path: Path | None, encoding: str) -> Any | None:
    if path is None:
        return None

    with open(path, mode="r", encoding=encoding) as f:
        return json.load(f)


def _parse_json_file_into(path: Path, model: Type[_M], encoding: str) -> _M:
    with open(path, mode="r", encoding=encoding) as f:
        return model(**json.load(f))


def _maybe_parse_json_file_into(path: Path | None, model: Type[_M], encoding: str) -> _M | None:
    if path is None:
        return None

    return _parse_json_file_into(path, model, encoding)


def _destructure_context(ctx: click.Context) -> tuple[str, int, int, str, str]:
    """
    Collect all parameters passed into the main command.
    
    Args:
        ctx: Click context

    Returns:
        Tuple containing base URL, batch size, request timeout in seconds, CSV delimiter and file encoding
    """
    return (
        ctx.obj["BASE_URL"],
        int(ctx.obj["BATCH_SIZE"]),
        int(ctx.obj["TIMEOUT_SECS"]),
        ctx.obj["DELIMITER"],
        ctx.obj["ENCODING"]
    )


def _mask_and_write_to_output_file(
        base_mask_request: BaseMaskRequest,
        entity_file_path: Path,
        output_file_path: Path,
        encoding: str,
        delimiter: str,
        entity_id_column: str,
        entity_value_column: str,
        batch_size: int,
        base_url: str,
        timeout_secs: int
):
    # read entities
    _, entities = _read_attribute_value_entity_file(entity_file_path, encoding, delimiter, entity_id_column)
    # determine indices
    idx = list(range(0, len(entities), batch_size))

    with open(output_file_path, mode="w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, delimiter=delimiter, fieldnames=[entity_id_column, "value"])
        writer.writeheader()

        with click.progressbar(idx, label="Masking entities") as progressbar:
            for i in progressbar:
                mask_response = lib.mask(
                    base_mask_request.with_entities(entities[i:i + batch_size]),
                    base_url=base_url, timeout_secs=timeout_secs
                )

                writer.writerows([
                    {
                        entity_id_column: entity.id,
                        entity_value_column: entity.value
                    } for entity in mask_response.entities
                ])


@click.group()
@click.pass_context
@click.option(
    "--base-url", default="http://localhost:8000",
    help="base URL to HTTP-based PPRL service"
)
@click.option(
    "-b", "--batch-size", type=click.IntRange(min=1), default=1_000,
    help="amount of bit vectors to match at a time"
)
@click.option(
    "--timeout-secs", type=click.IntRange(min=1), default=30,
    help="seconds until a request times out"
)
@click.option(
    "--delimiter", type=str, default=",",
    help="column delimiter for CSV files"
)
@click.option(
    "--encoding", type=str, default="utf-8",
    help="character encoding for files"
)
def app(ctx: click.Context, base_url: str, batch_size: int, timeout_secs: int, delimiter: str, encoding: str):
    """HTTP client for performing PPRL based on Bloom filters."""
    ctx.ensure_object(dict)
    ctx.obj["BASE_URL"] = base_url
    ctx.obj["BATCH_SIZE"] = batch_size
    ctx.obj["TIMEOUT_SECS"] = timeout_secs
    ctx.obj["DELIMITER"] = delimiter
    ctx.obj["ENCODING"] = encoding


def _read_bit_vector_entity_file(
        path: Path, encoding: str, delimiter: str, id_column: str, value_column: str
) -> list[BitVectorEntity]:
    """
    Read a CSV file containing bit vector entities.
    
    Args:
        path: path to CSV file
        encoding: file encoding
        delimiter: column delimiter
        id_column: name of ID column
        value_column: name of value column

    Returns:
        list of bit vector entities
    """
    with open(path, mode="r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)

        # noinspection PyTypeChecker
        return [
            BitVectorEntity(
                id=row[id_column],
                value=row[value_column],
            ) for row in reader
        ]


@app.command()
@click.pass_context
@click.argument("base_match_request_file_path", type=click.Path(exists=True, path_type=Path))
@click.argument("vector_file_path", type=click.Path(exists=True, path_type=Path, dir_okay=False), nargs=-1)
@click.argument("output_file_path", type=click.Path(path_type=Path, dir_okay=False))
@click.option(
    "--id-column", type=str, default="id",
    help="column name in input CSV file containing vector ID"
)
@click.option(
    "--value-column", type=str, default="value",
    help="column name in input CSV file containing vector value"
)
def match(
        ctx: click.Context,
        base_match_request_file_path: Path, vector_file_path: tuple[Path, ...], output_file_path: Path,
        id_column: str, value_column: str,
):
    """
    Match bit vectors from CSV files against each other.

    BASE_MATCH_REQUEST_FILE_PATH is the path to a JSON file containing the base match request.
    VECTOR_FILE_PATH is the path to a CSV file containing bit vectors.
    At least two files must be specified.
    OUTPUT_FILE_PATH is the path of the CSV file where the matches should be written to.
    """
    if len(vector_file_path) < 2:
        click.echo("Must specify at least two CSV files containing vectors", err=True)
        ctx.exit(1)

    base_url, batch_size, timeout_secs, delimiter, encoding = _destructure_context(ctx)
    base_match_request = _parse_json_file_into(base_match_request_file_path, BaseMatchRequest, encoding)

    vectors_lst = [_read_bit_vector_entity_file(
        path, encoding, delimiter, id_column, value_column
    ) for path in vector_file_path]

    with open(output_file_path, mode="w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, delimiter=delimiter, fieldnames=[
            "domain_id", "domain_file", "range_id", "range_file", "similarity"
        ])

        writer.writeheader()

        for i in range(0, len(vectors_lst) - 1):
            for j in range(i + 1, len(vectors_lst)):
                domain_vectors, range_vectors = vectors_lst[i], vectors_lst[j]
                domain_file_name, range_file_name = vector_file_path[i].name, vector_file_path[j].name

                domain_start_idx = list(range(0, len(domain_vectors), batch_size))
                range_start_idx = list(range(0, len(range_vectors), batch_size))
                idx_pairs = list(itertools.product(domain_start_idx, range_start_idx))

                with click.progressbar(
                        idx_pairs, label=f"Matching bit vectors from {domain_file_name} and {range_file_name}"
                ) as progressbar:
                    for idx_tpl in progressbar:
                        domain_idx, range_idx = idx_tpl[0], idx_tpl[1]

                        match_request = base_match_request.with_vectors(
                            domain_lst=domain_vectors[domain_idx:domain_idx + batch_size],
                            range_lst=range_vectors[range_idx:range_idx + batch_size]
                        )

                        match_response = lib.match(match_request, base_url=base_url, timeout_secs=timeout_secs)

                        writer.writerows([
                            {
                                "domain_id": matched_vectors.domain.id,
                                "domain_file": domain_file_name,
                                "range_id": matched_vectors.range.id,
                                "range_file": range_file_name,
                                "similarity": matched_vectors.similarity
                            } for matched_vectors in match_response.matches
                        ])


def _read_attribute_value_entity_file(
        entity_file_path: Path, encoding: str, delimiter: str, id_column: str
) -> tuple[list[str], list[AttributeValueEntity]]:
    with open(entity_file_path, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        csv_columns = list(reader.fieldnames)

        if id_column not in csv_columns:
            raise ValueError(f"Column {id_column} not found in CSV file {entity_file_path}")

        def _row_to_entity(row: dict[str, Any]) -> AttributeValueEntity:
            return AttributeValueEntity(
                id=str(row[id_column]),
                attributes={
                    # exclude ID column from attribute set
                    k: str(v) for k, v in row.items() if k != id_column
                }
            )

        # noinspection PyTypeChecker
        return csv_columns, [_row_to_entity(row) for row in reader]


@app.command()
@click.pass_context
@click.argument("base_transform_request_file_path", type=click.Path(exists=True, path_type=Path))
@click.argument("entity_file_path", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file_path", type=click.Path(path_type=Path, dir_okay=False))
@click.option(
    "--entity-id-column", type=str, default="id",
    help="column name in entity CSV file containing ID"
)
def transform(
        ctx: click.Context,
        base_transform_request_file_path: Path,
        entity_file_path: Path,
        output_file_path: Path,
        entity_id_column: str,
):
    """
    Perform pre-processing on a CSV file with entities.

    BASE_TRANSFORM_REQUEST_FILE_PATH is the path to a JSON file containing the base transform request.
    ENTITY_FILE_PATH is the path to the CSV file containing entities.
    OUTPUT_FILE_PATH is the path of the CSV file where the pre-processed entities should be written to.
    """
    base_url, batch_size, timeout_secs, delimiter, encoding = _destructure_context(ctx)

    # read entities
    csv_columns, entities = _read_attribute_value_entity_file(entity_file_path, encoding, delimiter, entity_id_column)
    base_transform_request = _parse_json_file_into(base_transform_request_file_path, BaseTransformRequest, encoding)

    idx = list(range(0, len(entities), batch_size))

    with open(output_file_path, "w", encoding=encoding, newline="") as output_file:
        writer = csv.DictWriter(output_file, delimiter=delimiter, fieldnames=csv_columns)
        writer.writeheader()

        with click.progressbar(idx, label="Transforming entities") as progressbar:
            for i in progressbar:
                transform_response = lib.transform(
                    base_transform_request.with_entities(entities[i:i + batch_size]),
                    base_url=base_url, timeout_secs=timeout_secs
                )

                writer.writerows([
                    {
                        entity_id_column: entity.id,
                        **entity.attributes
                    } for entity in transform_response.entities
                ])


@app.command()
@click.pass_context
@click.argument("base_mask_request_file_path", type=click.Path(exists=True, path_type=Path))
@click.argument("entity_file_path", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file_path", type=click.Path(dir_okay=False, file_okay=True, path_type=Path))
@click.option(
    "--entity-id-column",
    type=str, default="id", help="column name in entity CSV file containing ID"
)
@click.option(
    "--entity-value-column",
    type=str, default="value", help="column name in output CSV file containing vector value"
)
def mask(
        ctx: click.Context,
        base_mask_request_file_path: Path,
        entity_file_path: Path,
        output_file_path: Path,
        entity_id_column: str,
        entity_value_column: str
):
    """
    Mask a CSV file with entities.
    
    BASE_MASK_REQUEST_FILE_PATH is the path to a JSON file containing the base mask request.
    ENTITY_FILE_PATH is the path to the CSV file containing entities.
    OUTPUT_FILE_PATH is the path of the CSV file where the masked entities should be written to.
    """
    base_url, batch_size, timeout_secs, delimiter, encoding = _destructure_context(ctx)

    # read hardeners
    base_mask_request = _parse_json_file_into(base_mask_request_file_path, BaseMaskRequest, encoding)

    _mask_and_write_to_output_file(
        base_mask_request, entity_file_path, output_file_path,
        encoding, delimiter, entity_id_column, entity_value_column, batch_size, base_url, timeout_secs
    )


@app.group()
def estimate():
    """Estimate attribute weights based on randomly generated data."""
    pass


def _try_load_base_transform_request_or_default(
        base_transform_request_file_path: Path | None,
        encoding: str
) -> BaseTransformRequest:
    raw_req = _maybe_read_json(base_transform_request_file_path, encoding)

    if raw_req is None:
        return BaseTransformRequest(
            config=TransformConfig(empty_value=EmptyValueHandling.skip),
            global_transformers=GlobalTransformerConfig(before=[NormalizationTransformer()])
        )

    return BaseTransformRequest(**raw_req)


def _compute_stats_for_entities_and_write_to_file(
        entities: list[AttributeValueEntity],
        base_transform_request: BaseTransformRequest,
        attribute_config_output_file_path: Path,
        token_size: int,
        padding: str,
        base_url: str,
        timeout_secs: int,
        batch_size: int,
        encoding: str
):
    attribute_name_to_stats = lib.compute_attribute_stats(
        entities, base_transform_request,
        token_size=token_size, padding=padding, base_url=base_url, timeout_secs=timeout_secs, batch_size=batch_size
    )

    attribute_configs = [
        WeightedAttributeConfig(
            attribute_name=attribute_name,
            weight=attribute_stats.ngram_entropy,
            average_token_count=attribute_stats.average_tokens
        ) for attribute_name, attribute_stats in attribute_name_to_stats.items()
    ]

    with attribute_config_output_file_path.open("w", encoding=encoding) as f:
        json.dump([
            c.model_dump(exclude_none=True) for c in attribute_configs
        ], f, indent=2)


def common_estimate_options(fn):
    fn = click.option(
        "--base-transform-request-file-path", type=click.Path(exists=True, path_type=Path),
        help="path to file containing attribute-level and global transformer definitions"
    )(fn)
    fn = click.option(
        "-q", "--token-size", type=click.IntRange(min=2), default=2,
        help="size of tokens to split each attribute value into"
    )(fn)
    fn = click.option(
        "-p", "--padding", type=str, default="_",
        help="padding to use when splitting attribute values into tokens"
    )(fn)

    return fn


@estimate.command()
@click.pass_context
@click.argument("GENERATOR_CONFIG_FILE_PATH", type=click.Path(exists=True, path_type=Path))
@click.argument("ATTRIBUTE_CONFIG_OUTPUT_FILE_PATH", type=click.Path(path_type=Path))
@common_estimate_options
def gecko(
        ctx: click.Context,
        generator_config_file_path: Path,
        attribute_config_output_file_path: Path,
        base_transform_request_file_path: Path | None,
        token_size: int,
        padding: str,
):
    """
    Estimate attribute weights based on data generated by Gecko.
    
    GENERATOR_CONFIG_FILE_PATH is the file which defines the Gecko generators to use.
    ATTRIBUTE_CONFIG_OUTPUT_FILE_PATH is the path to the file where the attribute weights will be written to.
    """
    import inspect

    try:
        import gecko as gecko_lib
        import numpy as np
    except ImportError:
        click.echo("Gecko not found, install it with `pip install pprl_client[gecko]`", err=True)
        raise click.exceptions.Exit(1)

    base_url, batch_size, timeout_secs, _, encoding = _destructure_context(ctx)

    with generator_config_file_path.open(mode="r", encoding=encoding) as f:
        generator_config = GeckoGeneratorConfig(**json.load(f))

    base_transform_request = _try_load_base_transform_request_or_default(base_transform_request_file_path, encoding)

    rng = np.random.default_rng(generator_config.seed)
    column_to_generator_dict: dict[tuple[str, ...], gecko_lib.generator.Generator] = {}

    for generator in generator_config.generators:
        gen_factory_fn = getattr(gecko_lib.generator, generator.function_name, None)

        if not callable(gen_factory_fn):
            raise ValueError(f"invalid gecko function: {generator.function_name}")

        gen_factory_fn_args = copy.deepcopy(generator.args)
        gen_factory_fn_arg_spec = inspect.getfullargspec(gen_factory_fn)

        if "rng" in gen_factory_fn_arg_spec.args:
            gen_factory_fn_args["rng"] = rng

        attribute_name_tpl = tuple(generator.attribute_names)
        column_to_generator_dict[attribute_name_tpl] = gen_factory_fn(**gen_factory_fn_args)

    df_entities = gecko_lib.generator.to_data_frame(column_to_generator_dict, count=generator_config.count)

    entities = [
        AttributeValueEntity(
            id=str(entity_tpl[0]),
            attributes={
                k: str(v) for k, v in zip(df_entities.columns, entity_tpl[1:])
            }
        ) for entity_tpl in df_entities.itertuples()
    ]

    _compute_stats_for_entities_and_write_to_file(
        entities, base_transform_request, attribute_config_output_file_path, token_size, padding, base_url,
        timeout_secs, batch_size, encoding
    )


@estimate.command()
@click.pass_context
@click.argument("GENERATOR_CONFIG_FILE_PATH", type=click.Path(exists=True, path_type=Path))
@click.argument("ATTRIBUTE_CONFIG_OUTPUT_FILE_PATH", type=click.Path(path_type=Path))
@common_estimate_options
def faker(
        ctx: click.Context,
        generator_config_file_path: Path,
        attribute_config_output_file_path: Path,
        base_transform_request_file_path: Path | None,
        token_size: int,
        padding: str
):
    """
    Estimate attribute weights based on data generated by Faker.
    
    GENERATOR_CONFIG_FILE_PATH is the file which defines the Faker providers to use.
    ATTRIBUTE_CONFIG_OUTPUT_FILE_PATH is the path to the file where the attribute weights will be written to.
    """

    try:
        from faker import Faker
    except ImportError:
        click.echo("Faker not found, install it with `pip install pprl_client[faker]`", err=True)
        raise click.exceptions.Exit(1)

    base_url, batch_size, timeout_secs, _, encoding = _destructure_context(ctx)

    with generator_config_file_path.open(mode="r", encoding=encoding) as f:
        generator_config = FakerGeneratorConfig(**json.load(f))

    base_transform_request = _try_load_base_transform_request_or_default(base_transform_request_file_path, encoding)

    fake = Faker(generator_config.locale)
    fake.seed_instance(generator_config.seed)

    def _instantiate_faker_generator(generator: FakerGeneratorSpec):
        generator_fn = getattr(fake, generator.function_name, None)

        if not callable(generator_fn):
            raise ValueError(f"invalid faker function: {generator.function_name}")

        def _generate():
            return str(generator_fn(**generator.args))

        return _generate

    attribute_name_to_generator_fn: dict[str, Callable[[], str]] = {
        generator.attribute_name: _instantiate_faker_generator(generator)
        for generator in generator_config.generators
    }

    entities: list[AttributeValueEntity] = [
        AttributeValueEntity(
            id=str(i),
            attributes={
                attribute_name: generator_fn()
                for attribute_name, generator_fn in attribute_name_to_generator_fn.items()
            }
        ) for i in range(generator_config.count)
    ]

    _compute_stats_for_entities_and_write_to_file(
        entities, base_transform_request, attribute_config_output_file_path, token_size, padding, base_url,
        timeout_secs, batch_size, encoding
    )


def run_cli():
    app(max_content_width=120)


if __name__ == "__main__":
    run_cli()
