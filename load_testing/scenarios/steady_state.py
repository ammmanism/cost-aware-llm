# Steady state load test scenario
from locust import HttpUser, task, between

class SteadyStateUser(HttpUser):
    wait_time = between(2, 5)
    @task
    def request(self):
        self.client.post("/generate", json={"prompt": "Steady state test", "router": "cost_aware"})
