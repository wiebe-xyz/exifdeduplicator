# !./venv/bin/env python
import json
import os
import re
from datetime import datetime
from typing import Dict

import pyexiv2
import sys
import pathlib
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from connection import connection
from pika.exceptions import StreamLostError

exchange = 'exif_deduplicate'

filelist_queue = "exif_filelist"
exif_queue = "exif_exif"


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
        exif = read_metadata(path)

        ch.basic_publish(exchange=exchange, routing_key=exif_queue, body=bytes(json.dumps(exif), 'UTF-8'))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except (TypeError, AttributeError, FileNotFoundError) as e:
        print(f"{path} received error {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def read_metadata(path) -> Dict[str, str]:
    exif: Dict[str, str] = {'file': path}

    try:
        md = pyexiv2.ImageMetadata(path)
        md.read()
        date_key = 'Exif.Photo.DateTimeOriginal'
        make_key = 'Exif.Image.Make'
        model_key = 'Exif.Image.Model'

        if date_key in md.keys():
            exif['date'] = str(md.get(date_key).value)
        if model_key in md.keys():
            exif['model'] = md.get(model_key).value
        if make_key in md.keys():
            exif['make'] = md.get(make_key).value
    except Exception as e:
        print(f"could not read exif for {path}, received error {e}")

    stat = pathlib.Path(path).stat()
    exif['ctime'] = str(datetime.fromtimestamp(stat.st_birthtime))
    exif['mtime'] = str(datetime.fromtimestamp(stat.st_mtime))

    # if date is not in exif, it might be in the filename
    if "date" not in exif:
        pattern = re.compile('(\d{4}-\d{2}-\d{2})')
        match = pattern.search(path)
        if match:
            exif['date'] = match.group() + ' 00:00:00'
        else:
            exif['date'] = datetime.fromtimestamp(stat.st_birthtime).strftime('%Y-%m-%d %H:%M:%S')

    return exif


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
