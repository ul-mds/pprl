import csv
import json
import os
from pathlib import Path

import py
import pytest
from git import Repo
from pprl_model import GlobalTransformerConfig, NormalizationTransformer, AttributeTransformerConfig, \
    MappingTransformer, WeightedAttributeConfig, PermuteHardener, RehashHardener, StaticAttributeConfig, AttributeSalt, \
    BaseMaskRequest, MaskConfig, CLKFilter, HashConfig, HashFunction, HashAlgorithm, DoubleHash, RBFFilter, \
    CLKRBFFilter, BaseTransformRequest, TransformConfig, EmptyValueHandling, BaseMatchRequest, MatchConfig, \
    SimilarityMeasure, MatchMethod

from pprl_client.cli import app
from pprl_client.model import GeckoGeneratorConfig, GeckoGeneratorSpec
from tests.helpers import generate_person


@pytest.fixture(scope="module")
def gecko_data_path(tmpdir_factory):
    git_root_dir_path = tmpdir_factory.mktemp("git")
    repo = Repo.clone_from(
        "https://github.com/ul-mds/gecko-data.git",
        git_root_dir_path,
        no_checkout=True,
    )
    gecko_data_sha = os.environ.get("GECKO_DATA_SHA_COMMIT", "9b7a073caa4fedbc6917152454039d9e005a799c")
    repo.git.checkout(gecko_data_sha)

    yield git_root_dir_path


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


def _create_and_get_base_match_request_path(tmpdir: py.path.local, match_method: MatchMethod):
    base_match_request_path = tmpdir.join("match-request.json")
    base_match_request = BaseMatchRequest(
        config=MatchConfig(measure=SimilarityMeasure.jaccard, threshold=0, method=match_method)
    )

    with open(base_match_request_path, mode="w", encoding="utf-8") as f:
        json.dump(base_match_request.model_dump(exclude_none=True), f)

    return base_match_request_path


def test_match_crosswise(tmpdir: py.path.local, base64_factory, cli_runner, pprl_base_url,
                         env_pprl_request_timeout_secs):
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
        "match", str(_create_and_get_base_match_request_path(tmpdir, MatchMethod.crosswise)), str(domain_path),
        str(range_path),
        str(output_path)
    ])

    assert result.exit_code == 0
    assert output_path.check(file=1, exists=1, dir=0)

    with open(output_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {"domain_id", "domain_file", "range_id", "range_file", "similarity"}

        line_count = sum([1 for _ in reader])
        assert line_count == vector_count * vector_count


def test_match_with_single_file(
        tmpdir: py.path.local, base64_factory, cli_runner, pprl_base_url, env_pprl_request_timeout_secs
):
    domain_path = tmpdir.join("domain.csv")
    output_path = tmpdir.join("output.csv")

    _write_random_vectors_to(domain_path, base64_factory)
    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "--batch-size", "10", "--timeout-secs", str(env_pprl_request_timeout_secs),
        "match", str(_create_and_get_base_match_request_path(tmpdir, MatchMethod.crosswise)), str(domain_path),
        str(output_path)
    ])

    assert result.exit_code == 1
    assert "Must specify at least two CSV files containing vectors" in result.output


def test_match_with_multiple_files(
        tmpdir: py.path.local, base64_factory, cli_runner, pprl_base_url, env_pprl_request_timeout_secs
):
    vector_count = 50

    v1_path, v2_path, v3_path = tmpdir.join("vec1.csv"), tmpdir.join("vec2.csv"), tmpdir.join("vec3.csv")
    all_paths = (v1_path, v2_path, v3_path)

    for path in all_paths:
        _write_random_vectors_to(path, base64_factory, n=vector_count)

    # check that all files are unique
    assert len(set([path.computehash() for path in all_paths])) == len(all_paths)

    output_path = tmpdir.join("output.csv")
    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "--batch-size", "10", "--timeout-secs", str(env_pprl_request_timeout_secs),
        "match", str(_create_and_get_base_match_request_path(tmpdir, MatchMethod.crosswise)),
        str(v1_path), str(v2_path), str(v3_path), str(output_path),
    ])

    assert result.exit_code == 0
    assert output_path.check(file=1, exists=1, dir=0)

    with open(output_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {"domain_id", "domain_file", "range_id", "range_file", "similarity"}

        line_count = sum([1 for _ in reader])
        assert line_count == vector_count * vector_count * len(all_paths)


def test_match_pairwise(tmpdir: py.path.local, base64_factory, cli_runner, pprl_base_url,
                        env_pprl_request_timeout_secs):
    domain_path = tmpdir.join("domain.csv")
    range_path = tmpdir.join("range.csv")

    vector_count = 100

    _write_random_vectors_to(domain_path, base64_factory, n=vector_count)
    _write_random_vectors_to(range_path, base64_factory, n=vector_count)

    # check that different file were generated
    assert domain_path.computehash() != range_path.computehash()

    output_path = tmpdir.join("output.csv")
    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "--batch-size", "10", "--timeout-secs", str(env_pprl_request_timeout_secs),
        "match", str(_create_and_get_base_match_request_path(tmpdir, MatchMethod.pairwise)), str(domain_path),
        str(range_path),
        str(output_path)
    ])

    assert result.exit_code == 0
    assert output_path.check(file=1, exists=1, dir=0)

    with open(output_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {"domain_id", "domain_file", "range_id", "range_file", "similarity"}

        line_count = sum([1 for _ in reader])
        assert line_count == vector_count


def test_match_pairwise_error_on_mismatched_lengths(
        tmpdir: py.path.local, base64_factory, cli_runner, pprl_base_url,
        env_pprl_request_timeout_secs
):
    domain_path = tmpdir.join("domain.csv")
    range_path = tmpdir.join("range.csv")

    _write_random_vectors_to(domain_path, base64_factory, n=99)
    _write_random_vectors_to(range_path, base64_factory, n=100)

    # check that different file were generated
    assert domain_path.computehash() != range_path.computehash()

    output_path = tmpdir.join("output.csv")
    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "--batch-size", "10", "--timeout-secs", str(env_pprl_request_timeout_secs),
        "match", str(_create_and_get_base_match_request_path(tmpdir, MatchMethod.pairwise)), str(domain_path),
        str(range_path),
        str(output_path)
    ])

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == (
        "All bit vector files must have the same amount of vectors for pairwise matching, got: 99, 100"
    )


def test_transform(
        tmpdir: py.path.local, uuid4_factory, cli_runner, pprl_base_url, env_pprl_request_timeout_secs, faker
):
    # set up random entities
    entity_path = tmpdir.join("entities.csv")
    entity_count = 1_000

    _write_random_persons_to(entity_path, uuid4_factory, faker)

    base_transform_request_path = tmpdir.join("transform-request.json")
    base_transform_request = BaseTransformRequest(
        config=TransformConfig(empty_value=EmptyValueHandling.skip),
        global_transformers=GlobalTransformerConfig(
            before=[NormalizationTransformer()]
        ),
        attribute_transformers=[
            AttributeTransformerConfig(
                attribute_name="gender",
                transformers=[MappingTransformer(
                    mapping={
                        "male": "m",
                        "female": "f"
                    }
                )]
            )
        ]
    )

    with open(base_transform_request_path, "w", encoding="utf-8") as f:
        json.dump(base_transform_request.model_dump(exclude_none=True), f)

    output_path = tmpdir.join("output.csv")
    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "--batch-size", "100", "--timeout-secs", str(env_pprl_request_timeout_secs),
        "transform", str(base_transform_request_path), str(entity_path), str(output_path),
    ])

    assert result.exit_code == 0
    assert output_path.check(file=1, exists=1, dir=0)

    with open(output_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {"id", "first_name", "last_name", "date_of_birth", "gender"}

        line_count = sum([1 for _ in reader])
        assert line_count == entity_count


def _generate_entities_for_mask(tmpdir: py.path.local, uuid4_factory, faker, n=1_000):
    entity_path = tmpdir.join("entities.csv")
    _write_random_persons_to(entity_path, uuid4_factory, faker, n=n)

    return entity_path


def _generate_hardeners_for_mask():
    return [
        PermuteHardener(seed=727),
        RehashHardener(window_size=8, window_step=8, samples=2)
    ]


def _generate_attributes_for_mask(weighted: bool):
    if weighted:
        return [
            WeightedAttributeConfig(
                attribute_name="first_name",
                weight=4,
                average_token_count=10
            ),
            WeightedAttributeConfig(
                attribute_name="last_name",
                weight=4,
                average_token_count=8
            ),
            WeightedAttributeConfig(
                attribute_name="gender",
                weight=1,
                average_token_count=6
            ),
            WeightedAttributeConfig(
                attribute_name="date_of_birth",
                weight=2,
                average_token_count=10
            )
        ]
    else:
        return [
            StaticAttributeConfig(
                attribute_name="first_name",
                salt=AttributeSalt(value="foobar")
            )
        ]


def _check_mask_output(output_path: py.path.local, expected_line_count=1_000):
    assert output_path.check(file=1, exists=1, dir=0)

    with open(output_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {"id", "value"}

        line_count = sum([1 for _ in reader])
        assert line_count == expected_line_count


@pytest.mark.parametrize(
    "base_mask_request",
    [
        BaseMaskRequest(
            config=MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(algorithms=[HashAlgorithm.sha256]),
                    strategy=DoubleHash()
                ),
                prepend_attribute_name=True,
                filter=CLKFilter(filter_size=512, hash_values=5),
                padding="_",
                hardeners=_generate_hardeners_for_mask()
            ),
            attributes=_generate_attributes_for_mask(weighted=False)
        ),
        BaseMaskRequest(
            config=MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(algorithms=[HashAlgorithm.sha256]),
                    strategy=DoubleHash()
                ),
                prepend_attribute_name=True,
                filter=RBFFilter(hash_values=5, seed=727),
                padding="_",
                hardeners=_generate_hardeners_for_mask()
            ),
            attributes=_generate_attributes_for_mask(weighted=True)
        ),
        BaseMaskRequest(
            config=MaskConfig(
                token_size=2,
                hash=HashConfig(
                    function=HashFunction(algorithms=[HashAlgorithm.sha256]),
                    strategy=DoubleHash()
                ),
                prepend_attribute_name=True,
                filter=CLKRBFFilter(hash_values=5),
                padding="_",
                hardeners=_generate_hardeners_for_mask()
            ),
            attributes=_generate_attributes_for_mask(weighted=True)
        )
    ],
    ids=["clk", "rbf", "clkrbf"]
)
def test_mask(
        base_mask_request, tmpdir: py.path.local, uuid4_factory, cli_runner, pprl_base_url,
        env_pprl_request_timeout_secs, faker
):
    entity_count = 1_000
    entity_path = _generate_entities_for_mask(tmpdir, uuid4_factory, faker, n=entity_count)

    output_path = tmpdir.join("output.csv")
    mask_request_path = tmpdir.join("mask-request.json")

    with open(mask_request_path, mode="w", encoding="utf-8") as f:
        json.dump(base_mask_request.model_dump(exclude_none=True), f)

    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "--batch-size", "100", "--timeout-secs", str(env_pprl_request_timeout_secs),
        "mask", str(mask_request_path), str(entity_path), str(output_path)
    ])

    assert result.exit_code == 0
    _check_mask_output(output_path, entity_count)


def _check_estimate_output(output_path: py.path.local):
    with open(output_path, mode="r", encoding="utf-8") as f:
        output_data = json.load(f)

    output_configs = [WeightedAttributeConfig(**m) for m in output_data]

    # check that result is not empty
    assert output_configs != []

    # check that all generated values are unique
    assert len(output_configs) == len(set([c.attribute_name for c in output_configs]))
    assert len(output_configs) == len(set([c.weight for c in output_configs]))
    assert len(output_configs) == len(set([c.average_token_count for c in output_configs]))


def test_estimate_faker(
        tmpdir: py.path.local, cli_runner, pprl_base_url, env_pprl_request_timeout_secs
):
    faker_config_file_path = Path(__file__).parent / "assets" / "faker-config.json"
    base_transform_request_file_path = Path(__file__).parent / "assets" / "base-transform-request.json"
    output_path = tmpdir.join("output.csv")

    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "--batch-size", "100", "--timeout-secs", str(env_pprl_request_timeout_secs),
        "estimate", "faker", str(faker_config_file_path), str(output_path),
        "--base-transform-request-file-path", str(base_transform_request_file_path)
    ])

    assert result.exit_code == 0
    _check_estimate_output(output_path)


def test_estimate_gecko(
        tmpdir: py.path.local, cli_runner, pprl_base_url, env_pprl_request_timeout_secs, gecko_data_path
):
    gecko_config = GeckoGeneratorConfig(
        seed=727,
        count=5_000,
        generators=[
            GeckoGeneratorSpec(
                attribute_names=["given_name", "gender"],
                function_name="from_multicolumn_frequency_table",
                args={
                    "csv_file_path": str(gecko_data_path / "de_DE" / "given-name-gender.csv"),
                    "value_columns": ["given_name", "gender"],
                    "freq_column": "count"
                }
            ),
            GeckoGeneratorSpec(
                attribute_names=["last_name"],
                function_name="from_frequency_table",
                args={
                    "csv_file_path": str(gecko_data_path / "de_DE" / "last-name.csv"),
                    "value_column": "last_name",
                    "freq_column": "count"
                }
            ),
            GeckoGeneratorSpec(
                attribute_names=["street_name", "municipality", "postcode"],
                function_name="from_multicolumn_frequency_table",
                args={
                    "csv_file_path": str(gecko_data_path / "de_DE" / "street-municipality-postcode.csv"),
                    "value_columns": [
                        "street_name",
                        "municipality",
                        "postcode"
                    ],
                    "freq_column": "count"
                }
            )
        ]
    )

    gecko_config_file_path = tmpdir.join("gecko-config.json")

    with open(gecko_config_file_path, mode="w", encoding="utf-8") as f:
        json.dump(gecko_config.model_dump(), f)

    base_transform_request_file_path = Path(__file__).parent / "assets" / "base-transform-request.json"
    output_path = tmpdir.join("output.csv")

    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "--batch-size", "100", "--timeout-secs", str(env_pprl_request_timeout_secs),
        "estimate", "gecko", str(gecko_config_file_path), str(output_path),
        "--base-transform-request-file-path", str(base_transform_request_file_path)
    ])

    assert result.exit_code == 0
    _check_estimate_output(output_path)
