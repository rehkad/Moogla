settings_received = None

def init(settings: dict):
    global settings_received
    settings_received = settings


def preprocess(text: str) -> str:
    prefix = settings_received.get("prefix", "") if settings_received else ""
    return prefix + text


def postprocess(text: str) -> str:
    suffix = settings_received.get("suffix", "") if settings_received else ""
    return text + suffix
