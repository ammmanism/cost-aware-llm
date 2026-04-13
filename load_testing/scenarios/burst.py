import time
from locust import HttpUser, task, between

class BurstUser(HttpUser):
    wait_time = between(0.1, 0.5) # Fast requests

    @task
    def burst(self):
        self.client.post("/generate", json={"prompt": "Burst test", "router": "fallback"})
