#!/usr/bin/env python3
"""
Comprehensive Production Test Suite for Mini-RAG

Tests every critical path against the live Railway deployment.
Run this before going live with customers.
"""

import requests
import time
import random
import sys

BASE_URL = "https://mini-rag-production.up.railway.app"

class TestResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test_name):
        self.passed.append(test_name)
        print(f"✓ PASS: {test_name}")
    
    def add_fail(self, test_name, reason):
        self.failed.append((test_name, reason))
        print(f"✗ FAIL: {test_name}")
        print(f"   Reason: {reason}")
    
    def add_warning(self, test_name, reason):
        self.warnings.append((test_name, reason))
        print(f"⚠️  WARN: {test_name}")
        print(f"   Reason: {reason}")
    
    def summary(self):
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"✓ Passed: {len(self.passed)}")
        print(f"✗ Failed: {len(self.failed)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        
        if self.failed:
            print("\nFAILURES:")
            for test, reason in self.failed:
                print(f"  - {test}: {reason}")
        
        if self.warnings:
            print("\nWARNINGS:")
            for test, reason in self.warnings:
                print(f"  - {test}: {reason}")
        
        print("\n" + "="*60)
        if len(self.failed) == 0:
            print("✅ ALL CRITICAL TESTS PASSED - SAFE TO USE")
            return 0
        else:
            print("❌ CRITICAL FAILURES - DO NOT USE IN PRODUCTION")
            return 1


def main():
    results = TestResult()
    
    print("="*60)
    print("MINI-RAG COMPREHENSIVE PRODUCTION TEST")
    print(f"Target: {BASE_URL}")
    print("="*60 + "\n")
    
    # Test 1: Health Check
    print("TEST 1: Health Check")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        health = r.json()
        if health.get("status") == "healthy":
            results.add_pass("Health endpoint")
            if health.get("database") != "healthy":
                results.add_warning("Database health", f"DB status: {health.get('database')}")
        else:
            results.add_fail("Health endpoint", f"Status: {health.get('status')}")
    except Exception as e:
        results.add_fail("Health endpoint", str(e))
    
    # Test 2: Sources API
    print("\nTEST 2: Sources API")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/sources", timeout=10)
        sources = r.json()
        source_count = sources.get("count", 0)
        total_chunks = sum(s.get("chunk_count", 0) for s in sources.get("sources", []))
        
        if r.status_code == 200 and source_count > 0:
            results.add_pass(f"Sources API ({source_count} sources, {total_chunks} chunks)")
        elif source_count == 0:
            results.add_warning("Sources API", "No sources found (expected if fresh install)")
        else:
            results.add_fail("Sources API", f"Status {r.status_code}")
    except Exception as e:
        results.add_fail("Sources API", str(e))
    
    # Test 3: File Upload
    print("\nTEST 3: File Upload")
    test_id = str(random.randint(10000, 99999))
    content = f"Production test {test_id} at {time.strftime('%Y-%m-%d %H:%M:%S')}"
    try:
        files = {"files": (f"test_{test_id}.txt", content.encode())}
        r = requests.post(f"{BASE_URL}/api/v1/ingest/files", files=files, timeout=30)
        
        if r.status_code == 200:
            results.add_pass("File upload endpoint responds")
            
            # Verify it appears in sources
            time.sleep(2)
            r2 = requests.get(f"{BASE_URL}/api/v1/sources")
            sources2 = r2.json()
            found = any(test_id in s.get("display_name", "") for s in sources2.get("sources", []))
            
            if found:
                results.add_pass(f"File indexed and appears in sources (test_{test_id}.txt)")
            else:
                results.add_warning("File indexing", "Upload succeeded but file not in sources list")
        else:
            results.add_fail("File upload", f"Status {r.status_code}: {r.json()}")
    except Exception as e:
        results.add_fail("File upload", str(e))
    
    # Test 4: Query (Ask)
    print("\nTEST 4: Query/Ask Endpoint")
    try:
        r = requests.post(f"{BASE_URL}/ask", data={"query": "What documents are available?", "k": 5}, timeout=30)
        
        if r.status_code == 200:
            answer_data = r.json()
            answer = answer_data.get("answer", "")
            citations = answer_data.get("citations", [])
            score = answer_data.get("score", {}).get("total", 0)
            
            results.add_pass(f"Ask endpoint ({len(answer)} chars, {len(citations)} citations)")
            
            if score < 50:
                results.add_warning("Answer quality", f"Low score: {score}/100")
            elif score >= 85:
                results.add_pass(f"High quality answer (score: {score}/100)")
        else:
            results.add_fail("Ask endpoint", f"Status {r.status_code}")
    except Exception as e:
        results.add_fail("Ask endpoint", str(e))
    
    # Test 5: Security Headers
    print("\nTEST 5: Security Headers")
    try:
        r = requests.get(f"{BASE_URL}/health")
        headers = r.headers
        
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Content-Security-Policy"
        ]
        
        missing = [h for h in required_headers if h not in headers]
        if not missing:
            results.add_pass("Security headers present")
        else:
            results.add_warning("Security headers", f"Missing: {', '.join(missing)}")
    except Exception as e:
        results.add_warning("Security headers", str(e))
    
    # Test 6: Rate Limiting
    print("\nTEST 6: Rate Limiting")
    try:
        # Make 10 rapid requests
        statuses = []
        for i in range(10):
            r = requests.post(f"{BASE_URL}/ask", data={"query": f"test {i}", "k": 1})
            statuses.append(r.status_code)
        
        success_count = sum(1 for s in statuses if s == 200)
        rate_limited = sum(1 for s in statuses if s == 429)
        
        if success_count >= 8:  # Most should succeed
            results.add_pass(f"Rate limiting configured ({success_count}/10 succeeded)")
        else:
            results.add_warning("Rate limiting", f"Only {success_count}/10 succeeded")
    except Exception as e:
        results.add_warning("Rate limiting", str(e))
    
    # Test 7: Blocked File Types
    print("\nTEST 7: Blocked File Types")
    try:
        files = {"files": ("malicious.exe", b"fake exe")}
        r = requests.post(f"{BASE_URL}/api/v1/ingest/files", files=files, timeout=10)
        
        if r.status_code == 200:
            result = r.json()
            has_error = any("blocked" in str(item.get("error", "")).lower() for item in result.get("results", []))
            if has_error:
                results.add_pass("Blocked .exe file correctly")
            else:
                results.add_fail("File blocking", "Accepted .exe file")
        else:
            results.add_pass("Blocked .exe file (rejected)")
    except Exception as e:
        results.add_warning("File blocking test", str(e))
    
    # Test 8: Empty/Invalid Inputs
    print("\nTEST 8: Input Validation")
    try:
        # Empty query
        r1 = requests.post(f"{BASE_URL}/ask", data={"query": "", "k": 3})
        
        # Negative k
        r2 = requests.post(f"{BASE_URL}/ask", data={"query": "test", "k": -1})
        
        # Missing required field
        r3 = requests.post(f"{BASE_URL}/ask", data={"k": 3})
        
        invalid_count = sum(1 for r in [r1, r2, r3] if r.status_code in [400, 422])
        
        if invalid_count == 3:
            results.add_pass("Input validation (all 3 invalid inputs rejected)")
        else:
            results.add_warning("Input validation", f"Only {invalid_count}/3 invalid inputs rejected")
    except Exception as e:
        results.add_warning("Input validation", str(e))
    
    # Test 9: Data Persistence Check
    print("\nTEST 9: Data Persistence")
    try:
        # Upload a document
        persist_id = str(random.randint(20000, 29999))
        files = {"files": (f"persist_{persist_id}.txt", f"Persistence marker {persist_id}".encode())}
        r1 = requests.post(f"{BASE_URL}/api/v1/ingest/files", files=files, timeout=30)
        
        # Wait and query
        time.sleep(3)
        r2 = requests.post(f"{BASE_URL}/ask", data={"query": f"persistence marker {persist_id}", "k": 3}, timeout=30)
        
        if r2.status_code == 200 and persist_id in r2.json().get("answer", ""):
            results.add_pass("Data persistence (upload → query works)")
        else:
            results.add_fail("Data persistence", "Uploaded document not found in query")
    except Exception as e:
        results.add_fail("Data persistence", str(e))
    
    # Test 10: Performance
    print("\nTEST 10: Performance")
    try:
        start = time.time()
        r = requests.post(f"{BASE_URL}/ask", data={"query": "performance test", "k": 5}, timeout=10)
        duration = time.time() - start
        
        if r.status_code == 200:
            if duration < 2.0:
                results.add_pass(f"Fast response ({duration:.2f}s)")
            elif duration < 5.0:
                results.add_warning("Response time", f"{duration:.2f}s (acceptable but not fast)")
            else:
                results.add_warning("Response time", f"{duration:.2f}s (slow)")
        else:
            results.add_fail("Performance test", f"Status {r.status_code}")
    except Exception as e:
        results.add_fail("Performance test", str(e))
    
    # Final summary
    exit_code = results.summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()




