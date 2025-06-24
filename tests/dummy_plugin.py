def preprocess(text: str) -> str:
    return text.upper()


def postprocess(text: str) -> str:
    return f"!!{text}!!"
