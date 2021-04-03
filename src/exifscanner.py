# !./venv/bin/env python
import json
import os
import pyexiv2
import sys

from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from connection import connection
from pika.exceptions import StreamLostError

exchange = 'deduplicate'

filelist_queue = "filelist"
exif_queue = "exif"


def read_exif_callback(
        ch: BlockingChannel,
        method: spec.Basic.Deliver,
        properties: spec.BasicProperties,
        body: bytes
) -> None:
    path = body.decode('UTF-8')

    if os.path.isdir(path):
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    try:
        md = pyexiv2.ImageMetadata(path)
        md.read()
        datetime_original = md.get('Exif.Photo.DateTimeOriginal').value
        make = str(md.get('Exif.Image.Make').value)
        model = str(md.get('Exif.Image.Model').value)

        exif = {
            'file': path,
            'date': str(datetime_original),
            'make': make,
            'model': model
        }

        print(f"exif: {exif}")
        ch.basic_publish(exchange=exchange, routing_key=exif_queue, body=bytes(json.dumps(exif), 'UTF-8'))

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except (TypeError, AttributeError, FileNotFoundError) as e:
        print(f"{path} received error {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    channel = connection.channel()

    channel.basic_qos(prefetch_count=1)

    channel.exchange_declare(exchange, durable=True)
    channel.queue_declare(queue=filelist_queue)
    channel.queue_declare(queue=exif_queue)

    channel.queue_bind(queue=filelist_queue, exchange=exchange)
    channel.queue_bind(queue=exif_queue, exchange=exchange)

    channel.basic_consume(filelist_queue, read_exif_callback, consumer_tag='exifscanner')
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
