import csv
import itertools
import json
from pathlib import Path
from typing import Any, TypeVar, Type

import click
from pprl_model import MatchConfig, BitVectorEntity, MatchRequest, EntityTransformConfig, AttributeValueEntity, \
    GlobalTransformerConfig, EntityTransformRequest, MaskConfig, CLKFilter, HashConfig, \
    HashFunction, EntityMaskRequest
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


@click.group()
@click.pass_context
@click.option("--base-url", default="http://localhost:8000")
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
@click.argument("domain_file_path", type=click.Path(exists=True, path_type=Path, dir_okay=False))
@click.argument("range_file_path", type=click.Path(exists=True, path_type=Path, dir_okay=False))
@click.argument("output_file_path", type=click.Path(path_type=Path, dir_okay=False))
@click.option(
    "--domain-id-column", type=str, default="id",
    help="column name in domain CSV file containing vector ID"
)
@click.option(
    "--domain-value-column", type=str, default="value",
    help="column name in domain CSV file containing vector value"
)
@click.option(
    "--range-id-column", type=str, default="id",
    help="column name in range CSV file containing vector ID"
)
@click.option(
    "--range-value-column", type=str, default="value",
    help="column name in range CSV file containing vector value"
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
        domain_file_path: Path, range_file_path: Path, output_file_path: Path,
        measure: str, threshold: float,
        domain_id_column: str, domain_value_column: str, range_id_column: str, range_value_column: str,
):
    base_url, batch_size, timeout_secs, delimiter, encoding = _destructure_context(ctx)

    # noinspection PyTypeChecker
    match_config = MatchConfig(
        measure=measure,
        threshold=threshold,
    )

    domain_vectors = _read_bit_vector_entity_file(
        domain_file_path, encoding, delimiter,
        id_column=domain_id_column, value_column=domain_value_column
    )

    range_vectors = _read_bit_vector_entity_file(
        range_file_path, encoding, delimiter,
        id_column=range_id_column, value_column=range_value_column
    )

    domain_start_idx = list(range(0, len(domain_vectors), batch_size))
    range_start_idx = list(range(0, len(range_vectors), batch_size))

    idx_pairs = list(itertools.product(domain_start_idx, range_start_idx))

    with open(output_file_path, "w", encoding=encoding, newline="") as output_file:
        writer = csv.DictWriter(output_file, delimiter=delimiter, fieldnames=["domain_id", "range_id", "similarity"])
        writer.writeheader()

        with click.progressbar(idx_pairs, label="Matching bit vectors") as progressbar:
            for idx_tpl in progressbar:
                domain_idx, range_idx = idx_tpl

                match_request = MatchRequest(
                    config=match_config,
                    domain=domain_vectors[domain_idx:domain_idx + batch_size],
                    range=range_vectors[range_idx:range_idx + batch_size],
                )

                match_response = lib.match(match_request, base_url=base_url, timeout_secs=timeout_secs)

                writer.writerows([
                    {
                        "domain_id": matched_vectors.domain.id,
                        "range_id": matched_vectors.range.id,
                        "similarity": matched_vectors.similarity,
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
    pass


def common_mask_options(fn):
    fn = click.option("-q", "--token-size", type=click.IntRange(min=2), default=2)(fn)
    fn = click.option("--prepend-attribute-name/--no-prepend-attribute-name", default=True)(fn)
    fn = click.option("-p", "--padding", type=str, default="")(fn)
    fn = click.option("--hash-strategy", type=click.Choice(
        ["double_hash", "enhanced_double_hash", "triple_hash", "random_hash"]
    ), default="random_hash")(fn)
    fn = click.option("-h", "--hash-algorithm", type=click.Choice([
        "md5", "sha1", "sha256", "sha512"
    ]), multiple=True, default=["sha256"])(fn)
    fn = click.option("-s", "--hash-key", type=str)(fn)
    fn = click.option(
        "--hardener-config-path", type=click.Path(exists=True, path_type=Path), default=None
    )(fn)
    fn = click.option("--attribute-config-path", type=click.Path(exists=True, path_type=Path), default=None)(fn)
    fn = click.option(
        "--entity-id-column", type=str, default="id",
        help="column name in entity CSV file containing ID"
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
):
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

    _, entities = _read_attribute_value_entity_file(entity_file_path, encoding, delimiter, entity_id_column)

    attribute_json = _maybe_read_json(attribute_config_path, encoding) or []
    idx = list(range(0, len(entities), batch_size))

    with open(output_file_path, mode="w", encoding=encoding, newline="") as output_file:
        writer = csv.DictWriter(output_file, delimiter=delimiter, fieldnames=[entity_id_column, "value"])
        writer.writeheader()

        with click.progressbar(idx, label="Masking entities") as progressbar:
            for i in progressbar:
                mask_response = lib.mask(EntityMaskRequest(
                    config=mask_config,
                    entities=entities[i:i + batch_size],
                    attributes=attribute_json,
                ), base_url=base_url, timeout_secs=timeout_secs)

                writer.writerows([
                    {
                        entity_id_column: entity.id,
                        "value": entity.value
                    } for entity in mask_response.entities
                ])


def run_cli():
    app(max_content_width=120)


if __name__ == "__main__":
    run_cli()
