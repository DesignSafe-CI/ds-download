FROM python:3.13-bookworm

EXPOSE 8000

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

ENV PYSETUP_PATH="/opt/pysetup"
ENV PATH="$PYSETUP_PATH/.venv/bin:$PATH"
WORKDIR $PYSETUP_PATH

COPY pyproject.toml uv.lock ./
RUN uv sync --locked

RUN groupadd --gid 816877 G-816877 && \
    useradd --uid 458981 --gid G-816877 -m --shell /bin/bash tg458981 -d /home/tg458981

USER tg458981

COPY ./server/ /srv/www/server/

WORKDIR /srv/www/server
