# Import Celery app so it is loaded when Django starts.
# This ensures @shared_task decorators register properly.
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    pass
