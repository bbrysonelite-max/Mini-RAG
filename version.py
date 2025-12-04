"""
Application Version

VERSIONING RULES:
- MAJOR: Breaking changes, major rewrites
- MINOR: New features, significant improvements
- PATCH: Bug fixes, small improvements

UPDATE THIS FILE WITH EVERY RELEASE
"""

VERSION = "1.3.0"
BUILD_DATE = "2025-12-04"
COMMIT_HASH = "f8b04b1"  # Updated after commit

# Version info dict for API responses
VERSION_INFO = {
    "version": VERSION,
    "build_date": BUILD_DATE,
    "commit": COMMIT_HASH,
    "full_version": f"{VERSION} ({COMMIT_HASH})",
}
