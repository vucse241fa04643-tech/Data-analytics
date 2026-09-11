"""
Root pytest configuration for Agent 63 test suite.
Configures test-safe environment variables before any application modules are imported.
"""

import os

# Pytest session setup: Configure safe test defaults
os.environ.setdefault("JWT_SECRET", "test-suite-secure-jwt-secret-min-32-characters-for-testing-only")
os.environ.setdefault("ALLOW_TEST_FIXTURES", "true")

