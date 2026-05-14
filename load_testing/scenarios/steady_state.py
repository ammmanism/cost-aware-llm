# Steady state load test scenario
from locust import HttpUser, between, task


class SteadyStateUser(HttpUser):
    wait_time = between(2, 5)

    @task
    def request(self):
        self.client.post("/generate", json={"prompt": "Steady state test", "router": "cost_aware"})
