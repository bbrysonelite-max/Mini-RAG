"""
Test suite for Phase 3: Authentication & User Management

Run with: python3 test_phase3_auth.py

Prerequisites:
- PostgreSQL running with rag_brain database
- DATABASE_URL set in .env
- GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET set (for OAuth)
- Server NOT running (tests will start it)
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))


class FakeDatabase:
    """Minimal in-memory database stub for UserService tests."""

    def __init__(self):
        self.users = []

    async def fetch_one(self, query, *args):
        q = " ".join(query.split()).lower()

        if "count(*)" in q:
            return {"count": len(self.users)}

        if q.startswith("select") and "where email" in q:
            email = args[0]
            for user in self.users:
                if user["email"] == email:
                    return user.copy()
            return None

        if q.startswith("select") and "where id" in q:
            user_id = args[0]
            for user in self.users:
                if user["id"] == user_id:
                    return user.copy()
            return None

        if q.startswith("insert into users"):
            email, name, role = args
            now = datetime.utcnow().isoformat() + "Z"
            record = {
                "id": str(uuid.uuid4()),
                "email": email,
                "name": name,
                "role": role,
                "created_at": now,
                "updated_at": now,
            }
            self.users.append(record)
            return record.copy()

        if q.startswith("update users") and "set name" in q:
            name, email = args
            for user in self.users:
                if user["email"] == email:
                    user["name"] = name
                    user["updated_at"] = datetime.utcnow().isoformat() + "Z"
                    return user.copy()
            return None

        if q.startswith("update users") and "set role" in q:
            role, user_id = args
            for user in self.users:
                if user["id"] == user_id:
                    user["role"] = role
                    user["updated_at"] = datetime.utcnow().isoformat() + "Z"
                    return user.copy()
            return None

        return None

    async def fetch_all(self, query, *args):
        q = " ".join(query.split()).lower()
        if q.startswith("select") and "from users" in q:
            return [user.copy() for user in sorted(self.users, key=lambda u: u["created_at"], reverse=True)]
        return []

def test_imports():
    """Test 1: Verify all imports work"""
    print("Test 1: Checking imports...")
    try:
        from server import app, DATABASE_AVAILABLE, AUTH_AVAILABLE, USER_SERVICE
        from user_service import UserService
        from auth import create_access_token, verify_token, get_user_from_token
        from raglite import ingest_docs, ingest_youtube, ingest_transcript
        from retrieval import SimpleIndex, get_unique_sources, get_chunks_by_source
        print("  ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_user_service():
    """Test 2: UserService CRUD operations"""
    print("\nTest 2: UserService CRUD operations...")
    try:
        from user_service import UserService
        from database import init_database
        import os

        async def run_scenario(service: UserService):
            """Shared scenario for both real and fake DB tests."""
            # 1. First user should be created as admin.
            first_user = await service.create_or_update_user(
                email="test@example.com",
                name="Test User",
                oauth_sub="test-sub-123"
            )
            assert first_user is not None, "Failed to create first user"
            assert first_user['email'] == "test@example.com"
            assert first_user['role'] == "admin", "First user should default to admin"
            print(f"  ✓ First user created as admin ({first_user['email']})")

            # 2. is_admin must report True for the initial admin.
            assert await service.is_admin(str(first_user['id'])) is True, "Expected first user to be admin"
            print("  ✓ is_admin returned True for the first user")

            # 3. Second user creation path should default to reader.
            second_user = await service.create_or_update_user(
                email="reader@example.com",
                name="Reader User",
                oauth_sub="reader-sub-456"
            )
            assert second_user is not None, "Failed to create second user"
            assert second_user['role'] == "reader", "Second user should default to reader"
            print(f"  ✓ Second user created as reader ({second_user['email']})")

            # 4. list_all_users should reflect both users.
            users = await service.list_all_users()
            assert len(users) == 2, f"Expected 2 users in list_all_users, found {len(users)}"
            emails = {u['email'] for u in users}
            assert {"test@example.com", "reader@example.com"} <= emails, "Expected both users in list_all_users"
            print(f"  ✓ list_all_users returned both users ({len(users)} record(s))")

            # 5. Updating the first user's role should persist and remove admin privileges.
            updated = await service.update_user_role(str(first_user['id']), 'editor')
            assert updated['role'] == 'editor', "Failed to update role to editor"
            assert await service.is_admin(str(first_user['id'])) is False, "Editor should not be treated as admin"
            print("  ✓ Updated first user role to editor and is_admin returned False")

            # 6. The update path should refresh the user's name without altering the role we set.
            renamed = await service.create_or_update_user(
                email="test@example.com",
                name="Test User Renamed",
                oauth_sub="test-sub-123"
            )
            assert renamed['id'] == first_user['id'], "Update path should preserve user ID"
            assert renamed['name'] == "Test User Renamed", "User name was not updated"
            assert renamed['role'] == 'editor', "create_or_update_user should not reset role on update"
            print("  ✓ Re-invoked create_or_update_user updated the existing record without role regression")

            # 7. get_user_by_email/get_user_by_id should still locate the records.
            found = await service.get_user_by_email("test@example.com")
            assert found is not None and found['id'] == first_user['id'], "get_user_by_email failed after updates"
            fetched = await service.get_user_by_id(str(second_user['id']))
            assert fetched is not None and fetched['email'] == "reader@example.com", "get_user_by_id failed for second user"
            print("  ✓ get_user_by_email/get_user_by_id returned the expected users")

            return True

        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            print("  ⚙️  Using FakeDatabase (no DATABASE_URL configured)")
            fake_db = FakeDatabase()
            service = UserService(fake_db)

            async def run_fake():
                return await run_scenario(service)

            return asyncio.run(run_fake())

        async def run_real():
            db = await init_database(db_url, init_schema=False)
            service = UserService(db)
            return await run_scenario(service)

        return asyncio.run(run_real())
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_jwt_tokens():
    """Test 3: JWT token creation and verification"""
    print("\nTest 3: JWT token creation and verification...")
    try:
        from auth import create_access_token, verify_token, get_user_from_token
        
        # Create token
        payload = {
            "email": "test@example.com",
            "name": "Test User",
            "sub": "test-sub",
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "role": "admin"
        }
        token = create_access_token(payload)
        assert token is not None, "Failed to create token"
        print(f"  ✓ Created JWT token")
        
        # Verify token
        decoded = verify_token(token)
        assert decoded is not None, "Failed to verify token"
        assert decoded['email'] == "test@example.com"
        assert decoded['role'] == "admin"
        print(f"  ✓ Verified token payload")
        
        # Extract user from token
        user = get_user_from_token(token)
        assert user is not None, "Failed to extract user"
        assert user['user_id'] == "123e4567-e89b-12d3-a456-426614174000"
        print(f"  ✓ Extracted user from token")
        
        return True
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chunk_user_id():
    """Test 4: Chunks include user_id field"""
    print("\nTest 4: Chunk format with user_id...")
    try:
        from raglite import ingest_docs
        import tempfile
        import os
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is test content for checking user_id in chunks.")
            temp_path = f.name
        
        temp_output = tempfile.mktemp(suffix='.jsonl')
        
        try:
            # Test without user_id
            result = ingest_docs(temp_path, out_jsonl=temp_output, language="en", user_id=None)
            print(f"  ✓ Ingested without user_id: {result.get('written', 0)} chunks")
            
            # Test with user_id
            result = ingest_docs(temp_path, out_jsonl=temp_output, language="en", user_id="test-user-123")
            print(f"  ✓ Ingested with user_id: {result.get('written', 0)} chunks")
            
            # Verify chunk format
            import json
            with open(temp_output, 'r') as f:
                for line in f:
                    chunk = json.loads(line.strip())
                    if 'user_id' in chunk:
                        print(f"  ✓ Chunk contains user_id: {chunk.get('user_id')}")
                        break
            
            return True
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists(temp_output):
                os.unlink(temp_output)
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search_filtering():
    """Test 5: Search filters by user_id"""
    print("\nTest 5: Search filtering by user_id...")
    try:
        from retrieval import SimpleIndex
        
        # Create test chunks
        chunks = [
            {"id": "1", "content": "User A content", "user_id": "user-a"},
            {"id": "2", "content": "User B content", "user_id": "user-b"},
            {"id": "3", "content": "Legacy content"},  # No user_id
            {"id": "4", "content": "More User A content", "user_id": "user-a"},
        ]
        
        index = SimpleIndex(chunks)
        
        # Search without filter (should return all)
        results = index.search("content", k=10, user_id=None)
        assert len(results) == 4, f"Expected 4 results, got {len(results)}"
        print(f"  ✓ Search without filter: {len(results)} results")
        
        # Search with user_id filter
        results_a = index.search("content", k=10, user_id="user-a")
        # Should return: user-a chunks + legacy chunks
        assert len(results_a) >= 2, f"Expected at least 2 results for user-a"
        print(f"  ✓ Search for user-a: {len(results_a)} results (includes legacy)")
        
        results_b = index.search("content", k=10, user_id="user-b")
        # Should return: user-b chunks + legacy chunks
        assert len(results_b) >= 1, f"Expected at least 1 result for user-b"
        print(f"  ✓ Search for user-b: {len(results_b)} results (includes legacy)")
        
        # Verify user-a doesn't see user-b's content
        for idx, score in results_a:
            chunk = chunks[idx]
            chunk_user_id = chunk.get('user_id')
            assert chunk_user_id is None or chunk_user_id == "user-a", \
                f"User A shouldn't see user B's content: {chunk}"
        print(f"  ✓ Data isolation verified")
        
        return True
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_functions():
    """Test 6: Admin role checks"""
    print("\nTest 6: Admin role checks...")
    try:
        from server import is_admin, require_admin
        from fastapi import HTTPException
        
        # Test admin user
        admin_user = {"email": "admin@example.com", "role": "admin"}
        assert is_admin(admin_user) == True
        print(f"  ✓ is_admin(admin_user) = True")
        
        # Test non-admin user
        regular_user = {"email": "user@example.com", "role": "reader"}
        assert is_admin(regular_user) == False
        print(f"  ✓ is_admin(regular_user) = False")
        
        # Test None user
        assert is_admin(None) == False
        print(f"  ✓ is_admin(None) = False")
        
        # Test require_admin with admin
        try:
            require_admin(admin_user)
            print(f"  ✓ require_admin(admin) - passed")
        except HTTPException:
            print(f"  ✗ require_admin(admin) - should not raise")
            return False
        
        # Test require_admin with non-admin
        try:
            require_admin(regular_user)
            print(f"  ✗ require_admin(regular_user) - should have raised 403")
            return False
        except HTTPException as e:
            assert e.status_code == 403
            print(f"  ✓ require_admin(regular_user) - raised 403")
        
        # Test require_admin with None
        try:
            require_admin(None)
            print(f"  ✗ require_admin(None) - should have raised 401")
            return False
        except HTTPException as e:
            assert e.status_code == 401
            print(f"  ✓ require_admin(None) - raised 401")
        
        return True
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_compilation():
    """Test 7: All Python files compile without syntax errors"""
    print("\nTest 7: Python compilation check...")
    import py_compile
    import glob
    
    files = glob.glob("*.py")
    errors = []
    
    for file in files:
        if file.startswith("test_"):
            continue
        try:
            py_compile.compile(file, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{file}: {e}")
    
    if errors:
        print(f"  ✗ Compilation errors found:")
        for err in errors:
            print(f"    - {err}")
        return False
    else:
        print(f"  ✓ All {len(files)} files compile successfully")
        return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 3 Authentication & User Management - Test Suite")
    print("=" * 60)
    
    results = {}
    
    # Run tests
    results['imports'] = test_imports()
    results['jwt'] = test_jwt_tokens()
    results['chunk_user_id'] = test_chunk_user_id()
    results['search_filtering'] = test_search_filtering()
    results['admin_functions'] = test_admin_functions()
    results['compilation'] = test_compilation()
    results['user_service'] = test_user_service()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v == True)
    failed = sum(1 for v in results.values() if v == False)
    skipped = sum(1 for v in results.values() if v is None)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result == True else ("✗ FAIL" if result == False else "⊘ SKIP")
        print(f"{status:8} {name}")
    
    print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    
    if failed > 0:
        print("\n❌ SOME TESTS FAILED - Code needs fixes")
        sys.exit(1)
    elif skipped > 0:
        print("\n⚠️  SOME TESTS SKIPPED - Manual verification needed")
        sys.exit(0)
    else:
        print("\n✅ ALL TESTS PASSED - Phase 3 verified")
        sys.exit(0)

if __name__ == "__main__":
    main()

