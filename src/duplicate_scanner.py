# !./venv/bin/env python
import json
import sys
import imagehash
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from connection import connection
from pika.exceptions import StreamLostError
from PIL import Image

# from models import Duplicate, Similar

exchange = 'exif_deduplicate'

duplicates_queue = "exif_duplicates_queue"
exact_duplicate = "exif_exact_duplicate"
other_queue = "exif_other_duplicate"
similar_queue = "exif_similar_queue"


def duplicate_scanner_fallback(
        ch: BlockingChannel,
        method: spec.Basic.Deliver,
        properties: spec.BasicProperties,
        body: bytes
) -> None:
    exif = json.loads(body.decode('UTF-8'))

    try:
        # check the likeness of the image here we've got a couple of options here

        # md5 filematch, files are the exact same -> remove source

        # what to do with nef files (likeness through the roof but not the same)
        # nef files aren't matched with jpg right now because of the filename not matching,
        # but this will be a problem in the next step

        likeness = compare_images(exif)

        if likeness == 0:
            ch.basic_publish(exchange=exchange, routing_key=exact_duplicate, body=bytes(json.dumps(exif), 'UTF-8'))
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        if likeness >= 20:
            similar = exif
            similar['likeness'] = likeness
            ch.basic_publish(exchange=exchange, routing_key=similar_queue, body=bytes(json.dumps(similar), 'UTF-8'))
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # what we've got left are files with the same name and exif creation time
        # example; burst shots, 1970 creationdate, possibly

        ch.basic_publish(exchange=exchange, routing_key=other_queue, body=bytes(json.dumps(exif), 'UTF-8'))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except (TypeError, FileNotFoundError) as e:
        print(f"received error {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def compare_images(exif):
    # image likeness hash (check https://pypi.org/project/ImageHash/)
    hash = imagehash.average_hash(Image.open(exif['file']))
    # 5027 is a nested exact duplicate
    # 8402 is different (other angle == 20)
    # 8404 is tweaked a bit but has the same exif (difference == 4)
    otherhash = imagehash.average_hash(Image.open(exif['newpath']))
    likeness = hash - otherhash
    return likeness


def main():
    channel = connection.channel()

    channel.basic_qos(prefetch_count=1)

    channel.exchange_declare(exchange, durable=True)

    channel.queue_declare(queue=duplicates_queue)
    channel.queue_declare(queue=exact_duplicate)
    channel.queue_declare(queue=similar_queue)
    channel.queue_declare(queue=other_queue)

    channel.queue_bind(queue=duplicates_queue, exchange=exchange)
    channel.queue_bind(queue=exact_duplicate, exchange=exchange)
    channel.queue_bind(queue=similar_queue, exchange=exchange)
    channel.queue_bind(queue=other_queue, exchange=exchange)

    channel.basic_consume(duplicates_queue, duplicate_scanner_fallback, consumer_tag='duplicate_scanner')
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
