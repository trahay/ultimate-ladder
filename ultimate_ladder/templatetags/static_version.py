import hashlib
from functools import lru_cache

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


def file_version(path):
    """Short hash of the content of a static file."""
    full_path = finders.find(path)
    if full_path is None:
        return None
    with open(full_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()[:10]


cached_file_version = lru_cache(maxsize=None)(file_version)


@register.simple_tag
def static_version(path):
    """URL of a static file, with a version that changes when the file
    changes, so that browsers do not keep an old copy in their cache."""
    version = file_version(path) if settings.DEBUG else cached_file_version(path)
    url = static(path)
    return f'{url}?v={version}' if version else url
