FROM python:3.7
RUN apt-get update
RUN apt-get install -y build-essential
RUN apt-get install -y libboost-python-dev python-all-dev libexiv2-dev
RUN apt-get install -y cmake libboost-all-dev

ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

RUN groupadd -g 1000 app && useradd -rmu 1000 -g app app
RUN chown -R app:app /app
USER 1000

COPY requirements.txt .

RUN pip install -U setuptools wheel
RUN pip install -r requirements.txt

ADD . /app
WORKDIR /app/src
ENV PYTHONPATH=/app/src

CMD ['python', '/app/src/consumer.py', '--queue=download_stock_data']