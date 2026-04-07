from uuid import uuid4


def generate_id(prefix: str, length: int = 16) -> str:
    return ("-".join([prefix, uuid4().hex]))[:length]
