import asyncio

configured = {}

async def setup_async(settings: dict) -> None:
    await asyncio.sleep(0)
    configured.clear()
    configured.update(settings)


def postprocess(text: str) -> str:
    suffix = configured.get("suffix", "")
    return f"{text}{suffix}"
