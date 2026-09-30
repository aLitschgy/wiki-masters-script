FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    WIKIMASTERS_STATE_FILE=/data/session.json

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY auth.py display.py open_packs.py ./

# Non-root user; /data holds the session (mount it as a volume)
RUN adduser -D -u 1000 app && mkdir /data && chown app /data
USER app
VOLUME /data

ENTRYPOINT ["python", "open_packs.py"]
