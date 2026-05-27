#web: daphne DMDX_Django.asgi:application --port $PORT --bind 0.0.0.0 -v2

web: gunicorn DMDX_Django.wsgi:application --workers 2 --threads 4 --timeout 20

