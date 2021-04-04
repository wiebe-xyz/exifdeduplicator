# !./venv/bin/env python
import json
import shutil
import sys
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from connection import connection
from pika.exceptions import StreamLostError

exchange = 'exif_deduplicate'
exif_moved = "exif_moved"


def filemover_callback(
        ch: BlockingChannel,
        method: spec.Basic.Deliver,
        properties: spec.BasicProperties,
        body: bytes
) -> None:
    exif = json.loads(body.decode('UTF-8'))

    try:
        shutil.move(exif['newpath'] + '.meta', exif['targetpath'] + '.meta')
        shutil.move(exif['newpath'], exif['targetpath'])

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except (TypeError, FileNotFoundError) as e:
        print(f"received error {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    channel = connection.channel()

    channel.basic_qos(prefetch_count=1)

    channel.exchange_declare(exchange, durable=True)
    channel.queue_declare(queue=exif_moved)

    channel.queue_bind(queue=exif_moved, exchange=exchange)

    channel.basic_consume(exif_moved, filemover_callback, consumer_tag='rename_moved')
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
