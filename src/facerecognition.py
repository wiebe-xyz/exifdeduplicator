# !./venv/bin/env python
import json
import sys
import face_recognition

from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from connection import connection
from pika.exceptions import StreamLostError
from PIL import Image, UnidentifiedImageError

exchange = 'exif_deduplicate'
exif_face_recognition = "exif_face_recognition"


def face_recognition_callback(
        ch: BlockingChannel,
        method: spec.Basic.Deliver,
        properties: spec.BasicProperties,
        body: bytes
) -> None:
    exif = json.loads(body.decode('UTF-8'))

    try:
        filename = exif['newpath']
        image = face_recognition.load_image_file(filename)
        face_locations = face_recognition.face_locations(image)
        # face_landmarks_list = face_recognition.face_landmarks(image)

        # todo resize image to something smaller and use that to recognize faces

        # save the faces to a seperate file

        with Image.open(filename) as image:
            for i in range(len(face_locations)):
                face = face_locations[i]  # top , right, bottom, left
                face_box = (face[3], face[0], face[1], face[2])  # left, top, right, bottom

                face_crop = image.crop(face_box)
                # face_crop.convert('RGB')

                face_crop.save(f"{filename}-face-{i}.png")

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except (TypeError, FileNotFoundError, UnidentifiedImageError) as e:
        print(f"received error {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    channel = connection.channel()

    channel.basic_qos(prefetch_count=1)

    channel.exchange_declare(exchange, durable=True)
    channel.queue_declare(queue=exif_face_recognition)

    channel.queue_bind(queue=exif_face_recognition, exchange=exchange)

    channel.basic_consume(exif_face_recognition, face_recognition_callback, consumer_tag='face_recognition')
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
