import tomli

__version__ = None
with open("pyproject.toml", "rb") as f:
    pyproject = tomli.load(f)
    __version__ = pyproject["project"]["version"]