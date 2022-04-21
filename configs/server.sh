echo "[server.sh start]"

uwsgi \
    --http :5000 \
    --gevent 1000 \
    --http-websockets \
    --master --callable app --disable-logging \
    --wsgi-file /vantage6/vantage6-server/vantage6/server/wsgi.py \
    --pyargv /mnt/config.yaml

echo "[server.sh exit]"