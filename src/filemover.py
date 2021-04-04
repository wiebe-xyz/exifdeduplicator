# !./venv/bin/env python
import json
import os
import pathlib
import shutil
import sys
import time

from datetime import datetime
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from connection import connection
from pika.exceptions import StreamLostError

# from models import Exif, Duplicate

exchange = 'exif_deduplicate'
exif_queue = "exif_exif"
duplicates_queue = "exif_duplicates_queue"


def filemover_callback(
        ch: BlockingChannel,
        method: spec.Basic.Deliver,
        properties: spec.BasicProperties,
        body: bytes
) -> None:
    exif = json.loads(body.decode('UTF-8'))

    try:
        date = datetime.strptime(exif['date'], '%Y-%m-%d %H:%M:%S')

        # determine folder structure y/m/d/filename.extension
        basename = os.path.basename(exif['file'])
        ext = pathlib.Path(basename).suffix

        newpath = f"../data/target/{date.year}/{date.month}/{date.day}/{int(time.mktime(date.timetuple()))}--{basename}"

        # check if new path exists, if so this will complicate things (publish to duplicate checker)
        if pathlib.Path(newpath).exists():
            print(f"target file exists (possible duplicate) {newpath}")
            duplicate = exif
            duplicate['newpath'] = newpath
            ch.basic_publish(
                exchange=exchange,
                routing_key=duplicates_queue,
                body=bytes(json.dumps(duplicate), 'UTF-8')
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        print(f"date: {date}, basename: {basename}, extension: {ext}, newpath: {newpath}")
        os.makedirs(pathlib.Path(newpath).parent, exist_ok=True)
        shutil.move(exif['file'], newpath)

        # ch.basic_publish(exchange=exchange, routing_key=exif_queue, body=bytes(json.dumps(exif), 'UTF-8'))

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except (TypeError, FileNotFoundError) as e:
        print(f"received error {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    channel = connection.channel()

    channel.basic_qos(prefetch_count=1)

    channel.exchange_declare(exchange, durable=True)
    channel.queue_declare(queue=exif_queue)
    channel.queue_declare(queue=duplicates_queue)

    channel.queue_bind(queue=exif_queue, exchange=exchange)
    channel.queue_bind(queue=duplicates_queue, exchange=exchange)

    channel.basic_consume(exif_queue, filemover_callback, consumer_tag='filemover')
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
