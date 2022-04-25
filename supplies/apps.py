from django.apps import AppConfig
from flask import Flask
app = Flask(__name__)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%m/%d/%y'):
    return value.strftime(format)

# app.jinja_env.filters['datetimeformat'] = datetimeformat


class SuppliesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'supplies'
