from invoke.context import Context
from invoke.tasks import task


@task
def format(c: Context) -> None:  # noqa: A001
    c.run("ruff format")


@task
def lint(c: Context) -> None:
    c.run("ruff check --fix --show-fixes")


@task
def typecheck(c: Context) -> None:
    c.run("mypy")


@task
def test(c: Context) -> None:
    c.run("tox --parallel")
    c.run("coverage report -m --skip-covered")


@task(format, lint, typecheck, test)
def qa(c: Context) -> None:
    pass
