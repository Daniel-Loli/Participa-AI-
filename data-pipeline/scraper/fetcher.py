from __future__ import annotations

import time

import httpx

_USER_AGENT = "ParticipaAI-Scraper/1.0 (contact: participa.ai@hackathon.pe)"
_HEADERS = {"User-Agent": _USER_AGENT, "Accept-Language": "es-PE,es;q=0.9"}


class FetchError(Exception):
    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Error al obtener {url}: {reason}")


def fetch(url: str, timeout: int = 15) -> str:
    for attempt in range(2):
        try:
            # verify=False necesario para sitios gubernamentales peruanos con certs mal configurados
            response = httpx.get(url, headers=_HEADERS, timeout=timeout, follow_redirects=True, verify=False)
            if response.status_code >= 400:
                raise FetchError(url, f"HTTP {response.status_code}")
            time.sleep(1)
            return response.text
        except FetchError:
            raise
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            if attempt == 0:
                time.sleep(3)
                continue
            raise FetchError(url, str(exc)) from exc
        except httpx.HTTPError as exc:
            raise FetchError(url, str(exc)) from exc
