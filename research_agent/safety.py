import asyncio
import ipaddress
import re
import socket
from urllib.parse import urlsplit, urlunsplit

INJECTION = re.compile(
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions|"
    r"(system|developer)\s*(message|prompt)\s*:|<\|(?:im_start|system)|"
    r"<tool_call|\"(?:tool_calls|function_call)\"\s*:|"
    r"reveal\s+(your\s+)?(api.?key|secret)|exfiltrat", re.I)
STOPWORDS = set("the a an and or for to of in on with is are what how compare different top "
                "using use find summarize their pros cons building products question approaches "
                "please me about today latest current research which best".split())


def suspicious(text: str) -> bool:
    return bool(INJECTION.search(text))


def terms(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower())
            if len(word) > 2 and word not in STOPWORDS}


def canonical(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def public_url(url: str) -> tuple[str, int]:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("Only public HTTP(S) URLs without credentials are allowed")
    host = parts.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "%" in host:
        raise ValueError("Local host blocked")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    if port not in {80, 443}:
        raise ValueError("Non-web port blocked")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host, port
    if not address.is_global or address.is_multicast:
        raise ValueError("Non-public IP blocked")
    return host, port


async def resolve_public(url: str) -> tuple[str, str, int]:
    host, port = public_url(url)
    addresses = await asyncio.to_thread(socket.getaddrinfo, host, port, type=socket.SOCK_STREAM)
    ips = {entry[4][0] for entry in addresses}
    if not ips or any(not ipaddress.ip_address(ip).is_global or
                      ipaddress.ip_address(ip).is_multicast for ip in ips):
        raise ValueError("DNS returned a non-public address")
    return host, sorted(ips)[0], port
