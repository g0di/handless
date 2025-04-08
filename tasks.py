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
    c.run("pytest --cov --cov-report=term-missing")


@task(format, lint, typecheck, test)
def qa(c: Context) -> None:
    pass
