configured = {}


def setup(settings: dict) -> None:
    configured.clear()
    configured.update(settings)


def postprocess(text: str) -> str:
    suffix = configured.get("suffix", "")
    return f"{text}{suffix}"

