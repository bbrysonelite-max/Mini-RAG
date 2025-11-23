"""
Locust load testing scenarios for Mini-RAG.

Usage:
    pip install locust
    locust -f scripts/load_test.py --host http://localhost:8000
    
Then open http://localhost:8089 for the UI.
"""

import os
import random
from locust import HttpUser, task, between, events
from locust.exception import StopUser

# Configuration from environment
API_KEY = os.getenv("MINI_RAG_API_KEY", "")
TEST_QUERIES = [
    "What is RAG?",
    "How does vector search work?",
    "Explain embeddings",
    "What are the benefits of semantic search?",
    "How to optimize retrieval?",
]


class MiniRAGUser(HttpUser):
    """Simulates a typical user interacting with Mini-RAG."""
    
    # Wait 1-3 seconds between requests
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup before user starts making requests."""
        if not API_KEY:
            print("WARNING: MINI_RAG_API_KEY not set. Some tests will fail.")
        
        self.headers = {}
        if API_KEY:
            self.headers["X-API-Key"] = API_KEY
    
    @task(10)  # Weight: 10x more common than other tasks
    def ask_question(self):
        """Simulate asking a question."""
        query = random.choice(TEST_QUERIES)
        
        with self.client.post(
            "/api/v1/ask",
            data={"query": query, "k": 8},
            headers=self.headers,
            catch_response=True,
            name="/api/v1/ask"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "answer" in data:
                    response.success()
                else:
                    response.failure("No answer in response")
            elif response.status_code == 401:
                response.failure("Authentication required (set MINI_RAG_API_KEY)")
                raise StopUser()  # Stop this user if auth fails
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def list_sources(self):
        """List ingested sources."""
        with self.client.get(
            "/api/v1/sources",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/sources"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(1)
    def get_stats(self):
        """Get system stats."""
        with self.client.get(
            "/api/v1/stats",
            catch_response=True,
            name="/api/v1/stats"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "count" in data:
                    response.success()
                else:
                    response.failure("Missing count field")
            else:
                response.failure(f"Status: {response.status_code}")


class ReadOnlyUser(HttpUser):
    """User that only reads, no writes."""
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        if API_KEY:
            self.headers = {"X-API-Key": API_KEY}
        else:
            self.headers = {}
    
    @task
    def rapid_fire_questions(self):
        """Simulate rapid questioning (tests caching & dedup)."""
        query = random.choice(TEST_QUERIES)
        
        self.client.post(
            "/api/v1/ask",
            data={"query": query, "k": 5},
            headers=self.headers,
            name="/api/v1/ask [rapid]"
        )


class HealthCheckUser(HttpUser):
    """Simulates monitoring/health check probes."""
    
    wait_time = between(10, 30)  # Every 10-30s like a real health check
    
    @task
    def health_check(self):
        """Hit health endpoint."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    response.success()
                else:
                    response.failure(f"Unhealthy: {data}")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task
    def metrics_scrape(self):
        """Simulate Prometheus scraping metrics."""
        with self.client.get(
            "/metrics",
            catch_response=True,
            name="/metrics"
        ) as response:
            if response.status_code == 200 and "# HELP" in response.text:
                response.success()
            else:
                response.failure("Invalid metrics format")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print test configuration before starting."""
    print("=" * 60)
    print("Mini-RAG Load Test")
    print("=" * 60)
    print(f"Target: {environment.host}")
    print(f"API Key configured: {'Yes' if API_KEY else 'No (some tests will fail)'}")
    print(f"Test queries: {len(TEST_QUERIES)}")
    print("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Track custom metrics for specific scenarios."""
    # Log slow requests
    if response_time > 3000:  # 3 seconds
        print(f"⚠️  Slow request: {name} took {response_time}ms")
    
    # Track cache hits (if response headers include cache info)
    # This is optional - depends on your server implementation


if __name__ == "__main__":
    print("Run this with: locust -f scripts/load_test.py --host http://localhost:8000")
    print("Then open http://localhost:8089")

