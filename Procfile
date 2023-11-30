web: gunicorn DMDX_Django.wsgi --log-file -
worker: celery -A DMDX_Django worker -l info
