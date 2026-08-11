import socket
import unittest
from unittest.mock import patch

from backend.crawler.fetcher import fetch_public_page
from backend.crawler.url_safety import UnsafeUrlError, validate_public_http_url


def _dns_result(address: str, port: int = 443) -> list[tuple]:
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    return [(family, socket.SOCK_STREAM, 6, "", (address, port))]


class UrlSafetyTests(unittest.TestCase):
    @patch("backend.crawler.url_safety.socket.getaddrinfo")
    def test_allows_public_https_url(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _dns_result("93.184.216.34")

        validate_public_http_url("https://jobs.example.com/detail/1")

    @patch("backend.crawler.url_safety.socket.getaddrinfo")
    def test_blocks_private_and_metadata_addresses(self, getaddrinfo) -> None:
        for address in ("127.0.0.1", "10.0.0.8", "169.254.169.254", "::1"):
            with self.subTest(address=address):
                getaddrinfo.return_value = _dns_result(address)
                with self.assertRaises(UnsafeUrlError):
                    validate_public_http_url("https://jobs.example.com/detail/1")

    @patch("backend.crawler.url_safety.socket.getaddrinfo")
    def test_blocks_hostname_with_mixed_public_and_private_ips(self, getaddrinfo) -> None:
        getaddrinfo.return_value = [
            *_dns_result("93.184.216.34"),
            *_dns_result("192.168.1.10"),
        ]

        with self.assertRaises(UnsafeUrlError):
            validate_public_http_url("https://jobs.example.com/detail/1")

    def test_blocks_credentials_and_nonstandard_ports(self) -> None:
        with self.assertRaises(UnsafeUrlError):
            validate_public_http_url("https://user:password@example.com/job")

        with self.assertRaises(UnsafeUrlError):
            validate_public_http_url("https://example.com:8443/job")

    @patch("backend.crawler.fetcher.requests.Session")
    @patch("backend.crawler.url_safety.socket.getaddrinfo")
    def test_blocks_redirect_from_public_url_to_private_ip(self, getaddrinfo, session_class) -> None:
        getaddrinfo.side_effect = [
            _dns_result("93.184.216.34"),
            _dns_result("127.0.0.1", port=80),
        ]
        response = _FakeResponse(
            status_code=302,
            headers={"Location": "http://127.0.0.1/admin"},
        )
        session = _FakeSession(response)
        session_class.return_value = session

        with self.assertRaises(UnsafeUrlError):
            fetch_public_page("https://jobs.example.com/detail/1")

        self.assertEqual(session.request_count, 1)


class _FakeResponse:
    def __init__(self, status_code: int, headers: dict[str, str]) -> None:
        self.status_code = status_code
        self.headers = headers

    def close(self) -> None:
        pass


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.request_count = 0
        self.trust_env = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass

    def get(self, *args, **kwargs) -> _FakeResponse:
        self.request_count += 1
        return self.response


if __name__ == "__main__":
    unittest.main()
