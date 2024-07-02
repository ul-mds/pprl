import click


@click.group()
@click.option("--base-url", default="http://localhost:8000")
@click.pass_context
def app(ctx: click.Context, base_url: str):
    ctx.ensure_object(dict)
    ctx.obj["BASE_URL"] = base_url


if __name__ == "__main__":
    app()
