import random
from locust import HttpUser, TaskSet, task, between
from faker import Faker
import logging

fake = Faker()

class UserBehavior(TaskSet):
    product_ids = []

    def on_start(self):
        self.register_and_login()
        self.fetch_product_ids()

    def register_and_login(self):
        email = fake.unique.email()
        password = fake.password()
        
        # Garante que a requisição de registro seja reportada corretamente no Locust
        with self.client.post("/auth/register", json={"email": email, "password": password}, name="/auth/register", catch_response=True) as reg_response:
            if reg_response.status_code != 201:
                reg_response.failure(f"Registro falhou com status {reg_response.status_code} - {reg_response.text}")
                return # Interrompe se o registro falhar

        # Faz login com o usuário recém-criado
        with self.client.post("/auth/login", json={"email": email, "password": password}, name="/auth/login", catch_response=True) as login_response:
            if login_response.status_code != 200:
                login_response.failure(f"Login falhou com status {login_response.status_code} - {login_response.text}")

    def fetch_product_ids(self):
        try:
            with self.client.get("/products/", name="/products", catch_response=True) as response:
                if response.status_code == 200 and response.text:
                    products = response.json()
                    if products:
                        self.product_ids = [p['id'] for p in products]
                        response.success()
                    else:
                        response.failure("Nenhum produto encontrado")
                else:
                    response.failure(f"Falha ao buscar produtos: status {response.status_code}")
        except Exception as e:
            logging.error(f"Exceção ao buscar produtos: {e}")

    @task(10)
    def browse_products(self):
        self.client.get("/products/", name="/products")
        if self.product_ids:
            product_id = random.choice(self.product_ids)
            self.client.get(f"/products/{product_id}", name="/products/[id]")

    @task(5)
    def add_to_cart(self):
        if not self.product_ids:
            return
        product_id = random.choice(self.product_ids)
        self.client.post("/cart/", json={"product_id": product_id, "quantity": random.randint(1, 3)}, name="/cart")

    @task(3)
    def view_cart(self):
        self.client.get("/cart/", name="/cart")

    @task(2)
    def checkout_and_pay(self):
        if not self.product_ids:
            return

        product_id = random.choice(self.product_ids)
        self.client.post("/cart/", json={"product_id": product_id, "quantity": 1}, name="/cart (checkout)")
        
        order_id = None
        with self.client.post("/checkout/", name="/checkout", catch_response=True) as response:
            if response.status_code == 201:
                order_data = response.json()
                order_id = order_data.get("order_id")
                response.success()
            else:
                response.failure(f"Falha no checkout: {response.status_code} - {response.text}")
                return

        if order_id:
            with self.client.post(f"/payment/charge", json={"order_id": order_id}, name="/payment/charge", catch_response=True) as payment_response:
                if payment_response.status_code == 200:
                    payment_response.success()
                else:
                    payment_response.failure(f"Falha no pagamento: {payment_response.status_code}")

    @task(1)
    def view_orders(self):
        self.client.get("/orders/", name="/orders")


class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 5)