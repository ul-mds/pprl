import csv
import json

import py
from pprl_model import GlobalTransformerConfig, NormalizationTransformer, AttributeTransformerConfig, \
    MappingTransformer

from pprl_client.cli import app
from tests.helpers import generate_person


def _write_random_vectors_to(tmppath: py.path.local, base64_factory, n=1_000):
    with open(tmppath, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "value"])
        writer.writeheader()

        writer.writerows([
            {
                "id": str(i),
                "value": base64_factory(),
            } for i in range(n)
        ])


def _write_random_persons_to(tmppath: py.path.local, uuid4_factory, faker, n=1_000):
    with open(tmppath, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "first_name", "last_name", "date_of_birth", "gender"])
        writer.writeheader()

        persons = [generate_person(uuid4_factory(), faker) for _ in range(n)]

        writer.writerows(
            {
                "id": person.id,
                **person.attributes
            } for person in persons
        )


def test_match(tmpdir: py.path.local, base64_factory, cli_runner, pprl_base_url, env_pprl_request_timeout_secs):
    domain_path = tmpdir.join("domain.csv")
    range_path = tmpdir.join("range.csv")

    vector_count = 100

    _write_random_vectors_to(domain_path, base64_factory, n=vector_count)
    _write_random_vectors_to(range_path, base64_factory, n=vector_count)

    # Check that different files were actually generated.
    assert domain_path.computehash() != range_path.computehash()

    output_path = tmpdir.join("output.csv")
    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "--batch-size", "10", "--timeout-secs", str(env_pprl_request_timeout_secs),
        "match", str(domain_path), str(range_path), str(output_path),
        "-m", "jaccard", "-t", "0",
    ])

    assert result.exit_code == 0
    assert output_path.check(file=1, exists=1, dir=0)

    with open(output_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {"domain_id", "range_id", "similarity"}

        line_count = sum([1 for _ in reader])
        assert line_count == vector_count * vector_count


def test_transform(
        tmpdir: py.path.local, uuid4_factory, cli_runner, pprl_base_url, env_pprl_request_timeout_secs, faker
):
    # set up random entities
    entity_path = tmpdir.join("entities.csv")
    entity_count = 1_000

    _write_random_persons_to(entity_path, uuid4_factory, faker)

    # set up global attribute config
    global_json_path = tmpdir.join("global.json")

    with open(global_json_path, mode="w", encoding="utf-8") as f:
        json.dump(GlobalTransformerConfig(
            before=[NormalizationTransformer()]
        ).model_dump(), f)

    # set up attribute config
    attribute_json_path = tmpdir.join("attributes.json")

    with open(attribute_json_path, mode="w", encoding="utf-8") as f:
        json.dump([
            AttributeTransformerConfig(
                attribute_name="gender",
                transformers=[MappingTransformer(
                    mapping={
                        "male": "m",
                        "female": "f"
                    }
                )]
            ).model_dump()
        ], f)

    output_path = tmpdir.join("output.csv")
    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "--batch-size", "100", "--timeout-secs", str(env_pprl_request_timeout_secs),
        "transform", str(entity_path), str(output_path),
        "--global-config-path", str(global_json_path),
        "--attribute-config-path", str(attribute_json_path),
    ])

    assert result.exit_code == 0
    assert output_path.check(file=1, exists=1, dir=0)

    with open(output_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {"id", "first_name", "last_name", "date_of_birth", "gender"}

        line_count = sum([1 for _ in reader])
        assert line_count == entity_count
