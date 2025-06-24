FROM python:3.13-bookworm

EXPOSE 8000

COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

RUN groupadd --gid 816877 G-816877 && \
    useradd --uid 458981 --gid G-816877 -m --shell /bin/bash tg458981 -d /home/tg458981

USER tg458981

COPY ./server/ /srv/www/server/

WORKDIR /srv/www/server
