#web: daphne DMDX_Django.asgi:application --port $PORT --bind 0.0.0.0 -v2

# Basic dyno (512 MB): 2 workers × 3 threads ≈ 6 одночасних запитів без перевантаження RAM.
# timeout/graceful-timeout 20s < Heroku router 30s; max-requests — періодичний recycle workers.
web: gunicorn DMDX_Django.wsgi:application --bind 0.0.0.0:$PORT --worker-class gthread --workers 2 --threads 3 --timeout 20 --graceful-timeout 20 --max-requests 800 --max-requests-jitter 100 --worker-tmp-dir /dev/shm --log-file -
