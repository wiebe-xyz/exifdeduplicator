# !./venv/bin/env python
import glob
import sys
from connection import connection
from pika.exceptions import StreamLostError


def main():
    channel = connection.channel()
    queue = "filelist"
    channel.queue_declare(queue=queue)
    channel.basic_qos(prefetch_count=1)
    exchange = 'deduplicate'

    channel.exchange_declare(exchange, durable=True)
    channel.queue_bind(queue=queue, exchange=exchange)

    filelist = glob.glob('../data/source/**/*', recursive=True)
    for file in filelist:
        channel.basic_publish(routing_key=queue, exchange=exchange, body=file)

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
