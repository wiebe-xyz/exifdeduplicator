# !./venv/bin/env python
from typing import Callable, Optional
from connection import connection


import click
import sys
from pika.exceptions import StreamLostError

callbacks = {
    'read_exif_callback': None
}


@click.command()
@click.option('--queue', help='name of the queue to fetch messages from')
@click.option('--exchange', help='name of the exchange to bind the queue to')
@click.option('--ttl', help='ttl for messages published to this queue in seconds')
def main(
        queue: str,
        exchange: Optional[str],
        ttl: Optional[int]
) -> None:
    if not queue:
        help()
        exit(1)

    channel = connection.channel()
    arguments = {'x-message-ttl': int(ttl)} if ttl else {}

    channel.queue_declare(queue=queue, arguments=arguments)
    channel.basic_qos(prefetch_count=1)

    if exchange:
        channel.exchange_declare(exchange=exchange, exchange_type='fanout')
        channel.queue_bind(queue=queue, exchange=exchange)

    channel.basic_consume(queue=queue, on_message_callback=get_consumer(queue))

    channel.start_consuming()
    connection.close()


@click.command()
def help():
    for queue in callbacks.keys():
        print(queue)


def get_consumer(queue: str) -> Callable:
    return callbacks[queue]


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        sys.exit(0)
    except StreamLostError:
        print('RabbitMq connection lost')
        sys.exit(0)
