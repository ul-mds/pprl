import csv

import py

from pprl_client.cli import app


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


def test_match(tmpdir: py.path.local, base64_factory, cli_runner, pprl_base_url, env_pprl_request_timeout_secs):
    domain_path = tmpdir.join("domain.csv")
    range_path = tmpdir.join("range.csv")

    _write_random_vectors_to(domain_path, base64_factory)
    _write_random_vectors_to(range_path, base64_factory)

    # Check that different files were actually generated.
    assert domain_path.computehash() != range_path.computehash()

    output_path = tmpdir.join("output.csv")
    result = cli_runner.invoke(app, [
        "--base-url", pprl_base_url, "match",
        str(domain_path), str(range_path), str(output_path),
        "-m", "jaccard", "-t", "0", "--batch-size", "100", "--timeout-secs", str(env_pprl_request_timeout_secs)
    ])

    assert result.exit_code == 0
    assert output_path.check(file=1, exists=1, dir=0)

    with open(output_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {"domain_id", "range_id", "similarity"}

        line_count = sum([1 for _ in reader])
        assert line_count != 0
