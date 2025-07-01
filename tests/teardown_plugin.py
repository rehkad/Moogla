import asyncio

called = 0


async def teardown_async() -> None:
    await asyncio.sleep(0)
    global called
    called += 1
