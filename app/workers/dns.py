import logging

import dns.exception
import dns.resolver

from app.core.config import settings
from app.models.asset import AssetType

logger = logging.getLogger(__name__)

_RECORD_TYPES: tuple[AssetType, ...] = (
    AssetType.A,
    AssetType.AAAA,
    AssetType.NS,
    AssetType.MX,
)


def resolve_domain_records(domain_name: str) -> list[tuple[AssetType, str]]:
    """Resolve A/AAAA/NS/MX for a domain. Missing record types are skipped."""
    resolver = dns.resolver.Resolver()
    resolver.lifetime = settings.dns_timeout_seconds
    resolver.timeout = settings.dns_timeout_seconds

    results: list[tuple[AssetType, str]] = []
    for record_type in _RECORD_TYPES:
        try:
            answer = resolver.resolve(domain_name, record_type.value)
            for rdata in answer:
                if record_type == AssetType.MX:
                    value = str(rdata.exchange).rstrip(".")
                elif record_type in (AssetType.NS,):
                    value = str(rdata.target).rstrip(".")
                else:
                    value = rdata.to_text().rstrip(".")
                results.append((record_type, value))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            logger.info("No %s records for %s", record_type.value, domain_name)
        except dns.exception.Timeout as exc:
            logger.warning("Timeout resolving %s/%s: %s", domain_name, record_type.value, exc)
            raise
        except dns.exception.DNSException as exc:
            logger.warning("DNS error resolving %s/%s: %s", domain_name, record_type.value, exc)
            raise
    return results
