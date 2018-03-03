from datetime import datetime
from django.utils import timezone


def convert_timestamp(timestamp):
    """
    Returns a datetime object from a given timestamp
    """
    if timestamp:
        return datetime.fromtimestamp(timestamp, timezone.utc)
    return None
