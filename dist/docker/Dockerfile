FROM python:3.6-alpine

COPY ./requirements.txt /tmp/birch/requirements.txt
RUN pip install -r /tmp/birch/requirements.txt
RUN rm -r /tmp/birch

COPY ./birch /usr/local/lib/python3.6/birch
COPY ./birch_bin /usr/bin/birch
COPY ./config.ini /etc/Birch/config.ini

CMD ["/usr/bin/birch"]
