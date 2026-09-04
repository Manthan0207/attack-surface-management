import re

from fastapi import HTTPException, status

# Practical FQDN: lowercase labels, hyphens allowed, at least one dot.
_FQDN_RE = re.compile(
    r"^(?=.{1,253}$)"
    r"(?!-)[a-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[a-z0-9-]{1,63}(?<!-))+$"
)


def normalize_and_validate_fqdn(raw: str) -> str:
    """Normalize to lowercase and validate as an FQDN.

    Raises:
        HTTPException 400 if the value is not a valid FQDN.
    """
    domain = raw.strip().lower().rstrip(".")

    if not domain or not _FQDN_RE.fullmatch(domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid FQDN",
        )
    return domain
