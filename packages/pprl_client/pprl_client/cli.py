import csv
import itertools
import json
from pathlib import Path
from typing import Any, TypeVar, Type

import click
from pprl_model import MatchConfig, BitVectorEntity, MatchRequest, EntityTransformConfig, AttributeValueEntity, \
    GlobalTransformerConfig, EntityTransformRequest, MaskConfig, CLKFilter, HashConfig, \
    HashFunction, EntityMaskRequest, RBFFilter, CLKRBFFilter
from pydantic import BaseModel

from pprl_client import lib

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
        mask_config: MaskConfig,
        entity_file_path: Path,
        output_file_path: Path,
        attribute_config_file_path: Path | None,
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
    # read attribute json
    attribute_json = _maybe_read_json(attribute_config_file_path, encoding) or []
    # determine indices
    idx = list(range(0, len(entities), batch_size))

    with open(output_file_path, mode="w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, delimiter=delimiter, fieldnames=[entity_id_column, "value"])
        writer.writeheader()

        with click.progressbar(idx, label="Masking entities") as progressbar:
            for i in progressbar:
                mask_response = lib.mask(EntityMaskRequest(
                    config=mask_config,
                    entities=entities[i:i + batch_size],
                    attributes=attribute_json
                ), base_url=base_url, timeout_secs=timeout_secs)

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
@click.option(
    "-m", "--measure", type=click.Choice(["dice", "cosine", "jaccard"]), default="jaccard",
    help="similarity measure to use for comparing bit vector pairs"
)
@click.option(
    "-t", "--threshold", type=click.FloatRange(min=0, max=1), default=0.7,
    help="threshold at which to consider a bit vector pair a match"
)
def match(
        ctx: click.Context,
        vector_file_path: tuple[Path, ...], output_file_path: Path,
        measure: str, threshold: float,
        id_column: str, value_column: str,
):
    """
    Match bit vectors from CSV files against each other.

    VECTOR_FILE_PATH is the path to a CSV file containing bit vectors.
    At least two files must be specified.
    OUTPUT_FILE_PATH is the path of the CSV file where the matches should be written to.
    """
    if len(vector_file_path) < 2:
        click.echo("Must specify at least two CSV files containing vectors", err=True)
        ctx.exit(1)

    base_url, batch_size, timeout_secs, delimiter, encoding = _destructure_context(ctx)

    # noinspection PyTypeChecker
    match_config = MatchConfig(
        measure=measure,
        threshold=threshold,
    )

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

                        match_request = MatchRequest(
                            config=match_config,
                            domain=domain_vectors[domain_idx:domain_idx + batch_size],
                            range=range_vectors[range_idx:range_idx + batch_size],
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
@click.argument("entity_file_path", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file_path", type=click.Path(path_type=Path, dir_okay=False))
@click.option(
    "--entity-id-column", type=str, default="id",
    help="column name in entity CSV file containing ID"
)
@click.option(
    "--attribute-config-path", type=click.Path(exists=True, path_type=Path), default=None,
    help="path to JSON file containing attribute-level transformers"
)
@click.option(
    "--global-config-path", type=click.Path(exists=True, path_type=Path), default=None,
    help="path to JSON file containing global transformers"
)
@click.option(
    "--empty-value", type=click.Choice(["ignore", "error", "skip"]), default="error",
    help="handling of empty values during processing"
)
def transform(
        ctx: click.Context,
        entity_file_path: Path,
        output_file_path: Path,
        entity_id_column: str,
        empty_value: str,
        attribute_config_path: Path | None,
        global_config_path: Path | None
):
    """
    Perform pre-processing on a CSV file with entities.

    ENTITY_FILE_PATH is the path to the CSV file containing entities.
    OUTPUT_FILE_PATH is the path of the CSV file where the pre-processed entities should be written to.
    """
    base_url, batch_size, timeout_secs, delimiter, encoding = _destructure_context(ctx)

    # noinspection PyTypeChecker
    config = EntityTransformConfig(empty_value=empty_value)

    # read entities
    csv_columns, entities = _read_attribute_value_entity_file(entity_file_path, encoding, delimiter, entity_id_column)

    # read global config
    global_config = (_maybe_parse_json_file_into(global_config_path, GlobalTransformerConfig, encoding)
                     or GlobalTransformerConfig())

    attribute_config_json = _maybe_read_json(attribute_config_path, encoding) or []

    idx = list(range(0, len(entities), batch_size))

    with open(output_file_path, "w", encoding=encoding, newline="") as output_file:
        writer = csv.DictWriter(output_file, delimiter=delimiter, fieldnames=csv_columns)
        writer.writeheader()

        with click.progressbar(idx, label="Transforming entities") as progressbar:
            for i in progressbar:
                transform_response = lib.transform(EntityTransformRequest(
                    config=config, entities=entities[i:i + batch_size],
                    attribute_transformers=attribute_config_json,
                    global_transformers=global_config,
                ), base_url=base_url, timeout_secs=timeout_secs)

                writer.writerows([
                    {
                        entity_id_column: entity.id,
                        **entity.attributes
                    } for entity in transform_response.entities
                ])


@app.group()
def mask():
    """Mask a CSV file with entities."""
    pass


def common_mask_options(fn):
    fn = click.option(
        "-q", "--token-size", type=click.IntRange(min=2), default=2,
        help="size of tokens to split each attribute value into"
    )(fn)
    fn = click.option(
        "--prepend-attribute-name/--no-prepend-attribute-name", default=True,
        help="prepend attribute name to each token inserted into the filter"
    )(fn)
    fn = click.option(
        "-p", "--padding", type=str, default="",
        help="padding to use when splitting attribute values into tokens"
    )(fn)
    fn = click.option(
        "--hash-strategy", type=click.Choice(
            ["double_hash", "enhanced_double_hash", "triple_hash", "random_hash"]
        ), default="random_hash",
        help="strategy of setting bits in filter to use"
    )(fn)
    fn = click.option(
        "-h", "--hash-algorithm", type=click.Choice([
            "md5", "sha1", "sha256", "sha512"
        ]), multiple=True, default=["sha256"],
        help="hash algorithms to generate hash values with from tokens"
    )(fn)
    fn = click.option(
        "-s", "--hash-key", type=str, default=None,
        help="secret to use to turn select hash algorithms into keyed HMACs"
    )(fn)
    fn = click.option(
        "--hardener-config-path", type=click.Path(exists=True, path_type=Path), default=None,
        help="path to JSON file containing hardener configuration"
    )(fn)
    fn = click.option(
        "--attribute-config-path", type=click.Path(exists=True, path_type=Path), default=None,
        help="path to JSON file containing attribute configuration"
    )(fn)
    fn = click.option(
        "--entity-id-column", type=str, default="id",
        help="column name in entity CSV file containing ID"
    )(fn)
    fn = click.option(
        "--entity-value-column", type=str, default="value",
        help="column name in output CSV file containing vector value"
    )(fn)

    return fn


@mask.command()
@click.pass_context
@click.argument("entity_file_path", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file_path", type=click.Path(dir_okay=False, file_okay=True, path_type=Path))
@click.argument("filter_size", type=click.IntRange(min=1))
@click.argument("hash_values", type=click.IntRange(min=1))
@common_mask_options
def clk(
        ctx: click.Context,
        entity_file_path: Path,
        output_file_path: Path,
        filter_size: int,
        hash_values: int,
        token_size: int,
        prepend_attribute_name: bool,
        padding: str,
        hash_strategy: str,
        hash_algorithm: list[str],
        hash_key: str,
        hardener_config_path: Path | None,
        attribute_config_path: Path | None,
        entity_id_column: str,
        entity_value_column: str
):
    """
    Mask a CSV file with entities using a CLK filter.
    
    ENTITY_FILE_PATH is the path to the CSV file containing entities.
    OUTPUT_FILE_PATH is the path of the CSV file where the masked entities should be written to.
    FILTER_SIZE is the size of the CLK filter in bits.
    HASH_VALUES is the amount of hash values to generate per inserted token into the filter.
    """
    base_url, batch_size, timeout_secs, delimiter, encoding = _destructure_context(ctx)

    # read hardeners
    hardener_json = _maybe_read_json(hardener_config_path, encoding) or []

    # noinspection PyTypeChecker
    mask_config = MaskConfig(
        token_size=token_size,
        hash=HashConfig(
            function=HashFunction(
                algorithms=hash_algorithm,
                key=hash_key
            ),
            strategy={"name": hash_strategy}
        ),
        prepend_attribute_name=prepend_attribute_name,
        filter=CLKFilter(filter_size=filter_size, hash_values=hash_values),
        padding=padding,
        hardeners=hardener_json,
    )

    _mask_and_write_to_output_file(
        mask_config, entity_file_path, output_file_path,
        attribute_config_path, encoding, delimiter, entity_id_column, entity_value_column, batch_size, base_url,
        timeout_secs
    )


@mask.command()
@click.pass_context
@click.argument("entity_file_path", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file_path", type=click.Path(dir_okay=False, file_okay=True, path_type=Path))
@click.argument("hash_values", type=click.IntRange(min=1))
@click.argument("seed", type=int)
@common_mask_options
def rbf(
        ctx: click.Context,
        entity_file_path: Path,
        output_file_path: Path,
        hash_values: int,
        seed: int,
        token_size: int,
        prepend_attribute_name: bool,
        padding: str,
        hash_strategy: str,
        hash_algorithm: list[str],
        hash_key: str,
        hardener_config_path: Path | None,
        attribute_config_path: Path | None,
        entity_id_column: str,
        entity_value_column: str
):
    """
    Mask a CSV file with entities using an RBF filter.
    
    ENTITY_FILE_PATH is the path to the CSV file containing entities.
    OUTPUT_FILE_PATH is the path of the CSV file where the masked entities should be written to.
    HASH_VALUES is the minimum amount of hash values to generate per token inserted into the filter.
    The actual amount of hash values is computed using per-attribute configuration.
    SEED is the random number generator seed for randomly sampling bits to set in the filter. 
    """
    base_url, batch_size, timeout_secs, delimiter, encoding = _destructure_context(ctx)

    # read hardeners
    hardener_json = _maybe_read_json(hardener_config_path, encoding) or []

    # noinspection PyTypeChecker
    mask_config = MaskConfig(
        token_size=token_size,
        hash=HashConfig(
            function=HashFunction(
                algorithms=hash_algorithm,
                key=hash_key
            ),
            strategy={"name": hash_strategy}
        ),
        prepend_attribute_name=prepend_attribute_name,
        filter=RBFFilter(hash_values=hash_values, seed=seed),
        padding=padding,
        hardeners=hardener_json,
    )

    _mask_and_write_to_output_file(
        mask_config, entity_file_path, output_file_path,
        attribute_config_path, encoding, delimiter, entity_id_column, entity_value_column, batch_size, base_url,
        timeout_secs
    )


@mask.command()
@click.pass_context
@click.argument("entity_file_path", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file_path", type=click.Path(dir_okay=False, file_okay=True, path_type=Path))
@click.argument("hash_values", type=click.IntRange(min=1))
@common_mask_options
def clkrbf(
        ctx: click.Context,
        entity_file_path: Path,
        output_file_path: Path,
        hash_values: int,
        token_size: int,
        prepend_attribute_name: bool,
        padding: str,
        hash_strategy: str,
        hash_algorithm: list[str],
        hash_key: str,
        hardener_config_path: Path | None,
        attribute_config_path: Path | None,
        entity_id_column: str,
        entity_value_column: str
):
    """
    Mask a CSV file with entities using a CLKRBF filter.
    
    ENTITY_FILE_PATH is the path to the CSV file containing entities.
    OUTPUT_FILE_PATH is the path of the CSV file where the masked entities should be written to.
    HASH_VALUES is the minimum amount of hash values to generate per token inserted into the filter.
    The actual amount of hash values is computed using per-attribute configuration.
    """
    base_url, batch_size, timeout_secs, delimiter, encoding = _destructure_context(ctx)

    # read hardeners
    hardener_json = _maybe_read_json(hardener_config_path, encoding) or []

    # noinspection PyTypeChecker
    mask_config = MaskConfig(
        token_size=token_size,
        hash=HashConfig(
            function=HashFunction(
                algorithms=hash_algorithm,
                key=hash_key
            ),
            strategy={"name": hash_strategy}
        ),
        prepend_attribute_name=prepend_attribute_name,
        filter=CLKRBFFilter(hash_values=hash_values),
        padding=padding,
        hardeners=hardener_json,
    )

    _mask_and_write_to_output_file(
        mask_config, entity_file_path, output_file_path,
        attribute_config_path, encoding, delimiter, entity_id_column, entity_value_column, batch_size, base_url,
        timeout_secs
    )


def run_cli():
    app(max_content_width=120)


if __name__ == "__main__":
    run_cli()
