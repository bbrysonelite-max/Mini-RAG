"""
Application Version

VERSIONING RULES:
- MAJOR: Breaking changes, major rewrites
- MINOR: New features, significant improvements
- PATCH: Bug fixes, small improvements

UPDATE THIS FILE WITH EVERY RELEASE
"""

VERSION = "1.3.2"
BUILD_DATE = "2025-12-05"
COMMIT_HASH = "325f8b4"  # Fix 1: ID Wiring Restoration

# Version info dict for API responses
VERSION_INFO = {
    "version": VERSION,
    "build_date": BUILD_DATE,
    "commit": COMMIT_HASH,
    "full_version": f"{VERSION} ({COMMIT_HASH})",
}
