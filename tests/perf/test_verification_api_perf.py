# tests/perf/test_verification_api_perf.py
"""Run with: locust -f tests/perf/test_verification_api_perf.py --host http://localhost:8040"""
from locust import HttpUser, task, between

class VerificationApiUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def verify_supplier(self):
        r = self.client.get("/api/verify/123456789")
        assert r.status_code == 200
        assert r.elapsed.total_seconds() < 1.0, f"Response too slow: {r.elapsed.total_seconds():.2f}s"
