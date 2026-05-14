from locust import HttpUser, between, task


class LLMGatewayUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def generate(self):
        self.client.post(
            "/generate", json={"prompt": "Tell me a short joke", "tenant_id": "test_tenant"}
        )
