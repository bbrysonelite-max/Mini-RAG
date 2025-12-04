"""
Application Version

VERSIONING RULES:
- MAJOR: Breaking changes, major rewrites
- MINOR: New features, significant improvements
- PATCH: Bug fixes, small improvements

UPDATE THIS FILE WITH EVERY RELEASE
"""

VERSION = "1.0.0"
BUILD_DATE = "2025-12-03"
COMMIT_HASH = "4636ab4"  # Update with each release

# Version info dict for API responses
VERSION_INFO = {
    "version": VERSION,
    "build_date": BUILD_DATE,
    "commit": COMMIT_HASH,
    "full_version": f"{VERSION} ({COMMIT_HASH})",
}
