from locust import HttpUser, between, task


class APIUser(HttpUser):
    wait_time = between(1, 5)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def list_agents(self):
        self.client.get(
            "/v1/agents",
            headers={"Authorization": "Bearer dev-secret-key"},
        )

    @task(1)
    def list_calls(self):
        self.client.get(
            "/v1/calls",
            headers={"Authorization": "Bearer dev-secret-key"},
        )


class WriteUser(HttpUser):
    wait_time = between(2, 10)

    @task(2)
    def create_agent(self):
        self.client.post(
            "/v1/agents",
            json={
                "name": "Load Test Agent",
                "template_id": "tpl_receptionist_booking_v1",
                "timezone": "UTC",
                "default_language": "en",
                "business_hours": {"mon_fri": ["09:00-18:00"]},
            },
            headers={
                "Authorization": "Bearer dev-secret-key",
                "Idempotency-Key": f"locust-agent-{id(self)}",
            },
        )

    @task(1)
    def create_webhook(self):
        self.client.post(
            "/v1/webhooks",
            json={
                "target_url": "https://example.com/webhook",
                "event_types": ["call.ended"],
            },
            headers={
                "Authorization": "Bearer dev-secret-key",
                "Idempotency-Key": f"locust-webhook-{id(self)}",
            },
        )
