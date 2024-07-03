import csv
import itertools
from pathlib import Path

import click
from pprl_model import MatchConfig, BitVectorEntity, MatchRequest

from pprl_client import lib


@click.group()
@click.option("--base-url", default="http://localhost:8000")
@click.pass_context
def app(ctx: click.Context, base_url: str):
    ctx.ensure_object(dict)
    ctx.obj["BASE_URL"] = base_url


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
@click.option(
    "--delimiter", type=str, default=",",
    help="column delimiter in CSV file"
)
@click.option(
    "--encoding", type=str, default="utf-8",
    help="character encoding of CSV file"
)
@click.option(
    "-b", "--batch-size", type=click.IntRange(min=1), default=1_000,
    help="amount of bit vectors to match at a time"
)
def match(
        ctx: click.Context,
        domain_file_path: Path, range_file_path: Path, output_file_path: Path,
        measure: str, threshold: float,
        batch_size: int, domain_id_column: str, domain_value_column: str, range_id_column: str, range_value_column: str,
        delimiter: str, encoding: str,
):
    base_url = ctx.obj["BASE_URL"]

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

    idx_pairs = itertools.product(domain_start_idx, range_start_idx)

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

                match_response = lib.match(match_request, base_url=base_url)

                writer.writerows([
                    {
                        "domain_id": matched_vectors.domain.id,
                        "range_id": matched_vectors.range.id,
                        "similarity": matched_vectors.similarity,
                    } for matched_vectors in match_response.matches
                ])


def run_cli():
    app(max_content_width=120)


if __name__ == "__main__":
    run_cli()
