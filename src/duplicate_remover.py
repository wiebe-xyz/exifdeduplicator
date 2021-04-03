# !./venv/bin/env python
import json
import os
import sys
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from connection import connection
from pika.exceptions import StreamLostError
# from models import Duplicate

exchange = 'deduplicate'

exact_duplicate = "exact_duplicate"


def duplicate_remover(
        ch: BlockingChannel,
        method: spec.Basic.Deliver,
        properties: spec.BasicProperties,
        body: bytes
) -> None:
    exif = json.loads(body.decode('UTF-8'))

    try:
        # these files are duplicates, remove the source
        print(f"removing {exif['file']} as an exact duplicate of {exif['newpath']}")
        os.remove(exif['file'])

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except (TypeError, FileNotFoundError) as e:
        print(f"received error {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    channel = connection.channel()

    channel.basic_qos(prefetch_count=1)

    channel.exchange_declare(exchange, durable=True)
    channel.queue_declare(queue=exact_duplicate)
    channel.queue_bind(queue=exact_duplicate, exchange=exchange)

    channel.basic_consume(exact_duplicate, duplicate_remover, consumer_tag='duplicate_remover')
    channel.start_consuming()

    connection.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        sys.exit(0)
    except StreamLostError:
        print('RabbitMq connection lost')
        sys.exit(0)
