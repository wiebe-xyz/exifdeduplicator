import pika
from pika import BlockingConnection
from settings import settings

credentials = pika.PlainCredentials(settings['rabbit_user'], settings['rabbit_pass'])


def connect() -> BlockingConnection:
    return pika.BlockingConnection(
        pika.ConnectionParameters(settings['rabbit_host'], credentials=credentials)
    )


connection = connect()
