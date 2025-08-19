"""
WSGI config for food-ecommerce-web project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce_food_web.settings")

# Create the WSGI application
application = get_wsgi_application()

# Optional: Add whitenoise middleware for static files in production
# Uncomment the lines below if you're using whitenoise
# from whitenoise import WhiteNoise
# application = WhiteNoise(application)
