#!/usr/bin/env python3
"""
Admin CLI for issuing and managing API keys.

Usage:
  python scripts/manage_api_keys.py create --user USER_ID [--workspace WORKSPACE_ID] [--scope read --scope write] [--description "..."]
  python scripts/manage_api_keys.py list [--user USER_ID] [--workspace WORKSPACE_ID] [--include-revoked]
  python scripts/manage_api_keys.py revoke --id KEY_ID

Notes:
- The script expects DATABASE_URL to be set or will fall back to the default connection string.
- Plaintext API keys are only printed when a key is created; store them immediately and securely.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import List

from api_key_service import ApiKeyService, ApiKeyServiceError
from database import Database


async def _create_key(args: argparse.Namespace) -> None:
    db = Database()
    await db.initialize()
    service = ApiKeyService(db)

    try:
        result = await service.create_api_key(
            user_id=args.user,
            workspace_id=args.workspace,
            scopes=args.scope,
            description=args.description,
        )
    except ApiKeyServiceError as exc:
        await db.close()
        print(f"✗ Failed to create API key: {exc}", file=sys.stderr)
        sys.exit(1)

    await db.close()

    plaintext = result.pop("api_key", None)
    if not plaintext:
        print("✗ Unexpected error: API key was not returned", file=sys.stderr)
        sys.exit(1)

    print("✓ API key created successfully.\n")
    print("Store this key securely; it will not be shown again:\n")
    print(f"  API Key: {plaintext}\n")
    print("Metadata:")
    print(json.dumps(result, indent=2, default=str))


async def _list_keys(args: argparse.Namespace) -> None:
    db = Database()
    await db.initialize()
    service = ApiKeyService(db)

    try:
        rows = await service.list_api_keys(
            user_id=args.user,
            workspace_id=args.workspace,
            include_revoked=args.include_revoked,
        )
    except ApiKeyServiceError as exc:
        await db.close()
        print(f"✗ Failed to list API keys: {exc}", file=sys.stderr)
        sys.exit(1)

    await db.close()

    if not rows:
        print("No API keys found for the supplied filters.")
        return

    print(json.dumps(rows, indent=2, default=str))


async def _revoke_key(args: argparse.Namespace) -> None:
    db = Database()
    await db.initialize()
    service = ApiKeyService(db)

    try:
        updated = await service.revoke_api_key(args.id)
    except ApiKeyServiceError as exc:
        await db.close()
        print(f"✗ Failed to revoke API key: {exc}", file=sys.stderr)
        sys.exit(1)

    await db.close()

    if updated:
        print(f"✓ API key {args.id} revoked.")
    else:
        print(f"⚠ API key {args.id} was already revoked or does not exist.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage API keys.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create", help="Create a new API key")
    create.add_argument("--user", required=True, help="User ID (UUID) issuing the key")
    create.add_argument("--workspace", help="Workspace ID (UUID) the key belongs to")
    create.add_argument(
        "--scope",
        action="append",
        help="API scope(s) to grant (default: read). Supply multiple --scope flags.",
    )
    create.add_argument("--description", help="Optional description for tracking")

    list_cmd = sub.add_parser("list", help="List existing keys")
    list_cmd.add_argument("--user", help="Filter by user ID (UUID)")
    list_cmd.add_argument("--workspace", help="Filter by workspace ID (UUID)")
    list_cmd.add_argument(
        "--include-revoked",
        action="store_true",
        help="Show revoked keys as well",
    )

    revoke = sub.add_parser("revoke", help="Revoke an API key by ID")
    revoke.add_argument("--id", required=True, help="API key ID to revoke (UUID)")

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "create":
        asyncio.run(_create_key(args))
    elif args.cmd == "list":
        asyncio.run(_list_keys(args))
    elif args.cmd == "revoke":
        asyncio.run(_revoke_key(args))
    else:  # pragma: no cover - should not happen due to argparse
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

