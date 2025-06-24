import asyncio


async def preprocess_async(text: str) -> str:
    await asyncio.sleep(0)
    return text.upper()


async def postprocess_async(text: str) -> str:
    await asyncio.sleep(0)
    return f"<{text}>"
