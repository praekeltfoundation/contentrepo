import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python < 3.11
    import tomli as tomllib

from django import template

register = template.Library()


def _pyproject_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)
    return pyproject["project"]["version"]


@register.simple_tag
def contentrepo_version() -> str:
    try:
        return version("contentrepo")
    except PackageNotFoundError:
        return _pyproject_version()
