from importlib.metadata import PackageNotFoundError, version


def _resolve_version() -> str:
    try:
        return version("greyalien-prototype")
    except PackageNotFoundError:
        return "0.0.0+local"


__version__ = _resolve_version()
