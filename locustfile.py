from locust import HttpUser, task, between

class DjangoUser(HttpUser):
    # Each user waits 1-3 seconds between requests (simulates real browsing)
    wait_time = between(1, 3)

    @task(3)
    def home_page(self):
        """Visit the home page - most common action"""
        self.client.get("/")

    @task(2)
    def student_login_page(self):
        """Visit student login page"""
        self.client.get("/student/login/")

    @task(1)
    def ai_sathi_page(self):
        """Visit AI Sathi page"""
        self.client.get("/ai_sathi/")

    @task(1)
    def static_files(self):
        """Load static assets"""
        self.client.get("/static/school_app/images/pailogo.png")
