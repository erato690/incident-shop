import os

QUEUE_URL = os.environ.get("ESTOQUE_QUEUE_URL", "https://sqs.sa-east-1.example.com/estoque-reservas")
