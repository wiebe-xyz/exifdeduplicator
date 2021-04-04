# !./venv/bin/env python
import json
import os
import pathlib
import shutil
import sys
import time
import hashlib

from datetime import datetime
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from connection import connection
from pika.exceptions import StreamLostError

# from models import Exif, Duplicate

exchange = 'exif_deduplicate'
exif_queue = "exif_exif"
exif_moved = "exif_moved"
duplicates_queue = "exif_duplicates_queue"


def hashfile(file: str) -> str:
    block_size = 1024 * 1024 * 5  # The size of each read (5Mb) from the file

    file_hash = hashlib.sha256()
    with open(file, 'rb') as f:
        fb = f.read(block_size)
        while len(fb) > 0:
            file_hash.update(fb)
            fb = f.read(block_size)

    return file_hash.hexdigest()


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
        filename = pathlib.Path(basename).name
        exif['ext'] = ext
        exif['filename'] = filename

        # calculate hash for file and save the file with that name
        hash = hashfile(exif['file'])
        exif['hash'] = hash

        newpath = f"../data/target/{date.year}/{date.month}/{date.day}/{int(time.mktime(date.timetuple()))}--{hash}{ext}"
        targetpath = f"../data/target/{date.year}/{date.month}/{date.day}/{filename}{ext}"

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

        with open(newpath + ".meta", 'w+') as file:
            json.dump(exif, file)

        shutil.move(exif['file'], newpath)
        exif['newpath'] = newpath
        exif['targetpath'] = targetpath

        ch.basic_publish(exchange=exchange, routing_key=exif_moved, body=bytes(json.dumps(exif), 'UTF-8'))

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
    channel.queue_declare(queue=exif_moved)

    channel.queue_bind(queue=exif_queue, exchange=exchange)
    channel.queue_bind(queue=duplicates_queue, exchange=exchange)
    channel.queue_bind(queue=exif_moved, exchange=exchange)

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
