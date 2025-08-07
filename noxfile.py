import nox


@nox.session(python=False)
def fmt(session: nox.Session) -> None:
    session.run("ruff", "format")
    session.run("mdformat", ".")


@nox.session(python=False)
def lint(session: nox.Session) -> None:
    session.run("ruff", "check")


@nox.session(python=False)
def typecheck(session: nox.Session) -> None:
    session.run("mypy")


@nox.session(
    python=["3.13", "3.12", "3.11", "3.10"], venv_backend="uv", reuse_venv=True
)
def test(session: nox.Session) -> None:
    session.run_install(
        "uv",
        "sync",
        "--active",
        "--frozen",
        "--no-default-groups",
        "--group=test",
        external=True,
    )
    session.run("coverage", "run", "-m", "pytest", "-rN")
    session.notify("coverage")


@nox.session(python=False)
def coverage(session: nox.Session) -> None:
    session.run("coverage", "combine")
    session.run(
        "coverage", "report", "--skip-covered", "--skip-empty", "--show-missing"
    )
    session.run("coverage", "erase")
