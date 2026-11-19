"""Unit tests for IPv4/IPv6 validation, normalization, and payload rules."""

from __future__ import annotations

import unittest

from server.validation import ValidationError, normalize_ip_address, validate_ip_payload


class TestValidation(unittest.TestCase):
    def test_valid_ipv4_and_ipv6_canonicalization(self) -> None:
        self.assertEqual(normalize_ip_address(" 103.10.20.30 "), "103.10.20.30")
        self.assertEqual(normalize_ip_address("2001:0db8:0000:0000:0000:0000:0000:0001"), "2001:db8::1")

    def test_invalid_ip_rejected(self) -> None:
        for bad in ("", "999.999.1.1", "not-an-ip", "2001:db8:::1"):
            with self.assertRaises(ValidationError):
                normalize_ip_address(bad)

    def test_used_ip_requires_application_and_environment(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            validate_ip_payload(
                {
                    "ip_address": "103.10.20.10",
                    "provider": "Biznet",
                    "owner_type": "Internal",
                    "status": "Used",
                }
            )
        self.assertIn("application", ctx.exception.field_errors)
        self.assertIn("environment", ctx.exception.field_errors)

    def test_available_ip_allows_empty_application_domain_and_environment(self) -> None:
        cleaned = validate_ip_payload(
            {
                "ip_address": "103.10.20.12",
                "provider": "Telkom",
                "owner_type": "Internal",
                "status": "Available",
            }
        )
        self.assertEqual(cleaned["application"], "")
        self.assertEqual(cleaned["domain"], "")
        self.assertEqual(cleaned["environment"], "")

    def test_environment_and_enum_normalization(self) -> None:
        cleaned = validate_ip_payload(
            {
                "ip_address": "103.10.20.13",
                "provider": "AWS",
                "owner_type": "internal",
                "application": "Huly",
                "domain": "huly.company.id",
                "environment": "Prod",
                "server_ip": "10.0.1.20",
                "status": "used",
            }
        )
        self.assertEqual(cleaned["owner_type"], "Internal")
        self.assertEqual(cleaned["environment"], "prod")
        self.assertEqual(cleaned["status"], "Used")

    def test_invalid_enum_rejected(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            validate_ip_payload(
                {
                    "ip_address": "103.10.20.14",
                    "provider": "Biznet",
                    "owner_type": "Partner",
                    "environment": "qa",
                    "status": "Broken",
                }
            )
        self.assertIn("owner_type", ctx.exception.field_errors)
        self.assertIn("environment", ctx.exception.field_errors)
        self.assertIn("status", ctx.exception.field_errors)


if __name__ == "__main__":
    unittest.main()
