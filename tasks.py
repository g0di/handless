from invoke import task


@task
def format(c):
    c.run("ruff format")


@task
def lint(c):
    c.run("ruff check --fix --show-fixes")


@task
def test(c):
    c.run("pytest --cov --cov-report=term-missing")


@task(format, lint, test)
def qa(c):
    pass
