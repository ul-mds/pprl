import csv
import itertools
import json
from pathlib import Path
from typing import Any, TypeVar, Type

import click
from pprl_model import MatchConfig, BitVectorEntity, MatchRequest, EntityTransformConfig, AttributeValueEntity, \
    GlobalTransformerConfig, AttributeTransformerConfig, EntityTransformRequest
from pydantic import BaseModel

from pprl_client import lib

_M = TypeVar("_M", bound=BaseModel)


def _parse_json_file_into(path: Path, model: Type[_M], encoding: str) -> _M:
    with open(path, mode="r", encoding=encoding) as f:
        return model(**json.load(f))


def _maybe_parse_json_file_into(path: Path | None, model: Type[_M], encoding: str) -> _M | None:
    if path is None:
        return None

    return _parse_json_file_into(path, model, encoding)


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
    base_url = ctx.obj["BASE_URL"]
    batch_size = ctx.obj["BATCH_SIZE"]
    timeout_secs = ctx.obj["TIMEOUT_SECS"]
    delimiter = ctx.obj["DELIMITER"]
    encoding = ctx.obj["ENCODING"]

    # noinspection PyTypeChecker
    match_config = MatchConfig(
        measure=measure,
        threshold=threshold,
    )

    with open(domain_file_path, "r", encoding=encoding, newline="") as domain_file:
        reader = csv.DictReader(domain_file, delimiter=delimiter)

        # noinspection PyTypeChecker
        domain_vectors = [BitVectorEntity(
            id=row[domain_id_column],
            value=row[domain_value_column],
        ) for row in reader]

    with open(range_file_path, "r", encoding=encoding, newline="") as range_file:
        reader = csv.DictReader(range_file, delimiter=delimiter)
        # noinspection PyTypeChecker
        range_vectors = [BitVectorEntity(
            id=row[range_id_column],
            value=row[range_value_column],
        ) for row in reader]

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
    base_url = ctx.obj["BASE_URL"]
    batch_size = ctx.obj["BATCH_SIZE"]
    timeout_secs = ctx.obj["TIMEOUT_SECS"]
    delimiter = ctx.obj["DELIMITER"]
    encoding = ctx.obj["ENCODING"]

    # noinspection PyTypeChecker
    config = EntityTransformConfig(empty_value=empty_value)

    with open(entity_file_path, "r", encoding=encoding, newline="") as range_file:
        reader = csv.DictReader(range_file, delimiter=delimiter)
        csv_columns = reader.fieldnames

        if entity_id_column not in csv_columns:
            click.echo(f"Column {entity_id_column} not found in CSV file", err=True)
            ctx.exit(1)

        def _row_to_entity(row: dict[str, Any]) -> AttributeValueEntity:
            return AttributeValueEntity(
                id=str(row[entity_id_column]),
                attributes={
                    # exclude ID column from attribute set
                    k: str(v) for k, v in row.items() if k != entity_id_column
                }
            )

        # noinspection PyTypeChecker
        entities = [_row_to_entity(row) for row in reader]

    global_config = (_maybe_parse_json_file_into(global_config_path, GlobalTransformerConfig, encoding)
                     or GlobalTransformerConfig())

    if attribute_config_path is None:
        attribute_config = []
    else:
        with open(attribute_config_path, "r", encoding=encoding) as f:
            attribute_config = [AttributeTransformerConfig(**obj) for obj in json.load(f)]

    idx = list(range(0, len(entities), batch_size))

    with open(output_file_path, "w", encoding=encoding, newline="") as output_file:
        writer = csv.DictWriter(output_file, delimiter=delimiter, fieldnames=csv_columns)
        writer.writeheader()

        with click.progressbar(idx, label="Transforming entities") as progressbar:
            for i in progressbar:
                transform_response = lib.transform(EntityTransformRequest(
                    config=config, entities=entities[i:i + batch_size],
                    attribute_transformers=attribute_config,
                    global_transformers=global_config,
                ), base_url=base_url, timeout_secs=timeout_secs)

                writer.writerows([
                    {
                        entity_id_column: entity.id,
                        **entity.attributes
                    } for entity in transform_response.entities
                ])


def run_cli():
    app(max_content_width=120)


if __name__ == "__main__":
    run_cli()
