import os

# The application validates its JWT secret at import time. This value is
# intentionally scoped to the test process and must never be used in deployments.
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "ci-only-test-signing-key-0123456789abcdef0123456789abcdef",
)
