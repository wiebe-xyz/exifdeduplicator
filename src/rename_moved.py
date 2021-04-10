# !./venv/bin/env python
import json
import shutil
import sys
import os
import glob
import pathlib as pathlib
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from connection import connection
from pika.exceptions import StreamLostError

exchange = 'exif_deduplicate'
faces_recognized = "exif_faces_recognized"


def filemover_callback(
        ch: BlockingChannel,
        method: spec.Basic.Deliver,
        properties: spec.BasicProperties,
        body: bytes
) -> None:
    exif = json.loads(body.decode('UTF-8'))

    try:
        if not os.path.exists(exif['newpath']):
            print(f"file is already gone {exif['targetpath']} -> {exif['newpath']}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        if not os.path.exists(f"{exif['targetpath']}.json"):
            shutil.move(f"{exif['newpath']}.json", f"{exif['targetpath']}.json")

        if not os.path.exists(exif['targetpath']):
            shutil.move(exif['newpath'], exif['targetpath'])
        else:
            print(f"duplicate filename, skipping rename action for {exif['targetpath']}")

        # find files with -face-x
        path = pathlib.Path(exif['newpath']).parent
        filename = pathlib.Path(exif['newpath']).name
        extension = pathlib.Path(exif['newpath']).suffix

        basename = filename.split(extension)[0]
        targetfilename = pathlib.Path(exif['targetpath']).name.split(extension)[0]
        filelist = glob.glob(f"{path}/{basename}*-face*")

        for file in filelist:
            # target filename might already exist (broken or resized files for example)
            if not os.path.exists(targetfilename):
                shutil.move(file, str(file).replace(basename, targetfilename))

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except (TypeError, FileNotFoundError) as e:
        print(f"received error {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    channel = connection.channel()

    channel.basic_qos(prefetch_count=1)

    channel.exchange_declare(exchange, durable=True)
    channel.queue_declare(queue=faces_recognized)

    channel.queue_bind(queue=faces_recognized, exchange=exchange)

    channel.basic_consume(faces_recognized, filemover_callback, consumer_tag='rename_moved')
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
