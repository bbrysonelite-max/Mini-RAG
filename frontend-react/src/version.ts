/**
 * Application Version
 *
 * VERSIONING RULES:
 * - MAJOR: Breaking changes, major rewrites
 * - MINOR: New features, significant improvements
 * - PATCH: Bug fixes, small improvements
 *
 * UPDATE THIS FILE WITH EVERY RELEASE
 */

export const VERSION = '1.0.0';
export const BUILD_DATE = '2025-12-03';
export const COMMIT_HASH = '4636ab4'; // Update with each release

// Semantic version info
export const VERSION_INFO = {
  major: 1,
  minor: 0,
  patch: 0,
  prerelease: null as string | null, // e.g., 'beta.1', 'rc.1'
  build: BUILD_DATE.replace(/-/g, ''),
};

// Full version string for display
export const FULL_VERSION = VERSION_INFO.prerelease
  ? `${VERSION}-${VERSION_INFO.prerelease}`
  : VERSION;

// Version with build info
export const VERSION_WITH_BUILD = `${FULL_VERSION} (${COMMIT_HASH})`;
