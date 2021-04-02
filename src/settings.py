import os

from dotenv import load_dotenv
from pathlib import Path

env_path = str(Path(__file__).parent.parent.absolute()) + '/.env'
load_dotenv(dotenv_path=env_path)

settings = {
    'rabbit_user': os.getenv("RABBITMQ_DEFAULT_USER"),
    'rabbit_pass': os.getenv("RABBITMQ_DEFAULT_PASS"),
    'rabbit_host': os.getenv("RABBITMQ_HOST"),
}
