from hashlib import sha256

from fhir.resources.identifier import Identifier


def sha256_of_identifier(identifier: Identifier) -> str:
    return sha256(f"{identifier.system}|{identifier.value}".encode("utf-8")).hexdigest()
