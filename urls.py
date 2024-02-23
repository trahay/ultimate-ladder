"""
    urls.py
    ~~~~~~~
"""
from django.conf import settings
from django.urls import include, path
from django.views.static import serve

import ultimate_ladder


if settings.PATH_URL:
    urlpatterns = [
        path(f'{settings.PATH_URL}/', include('ultimate_ladder.urls')),
        path(f'{settings.PATH_URL}/<path:path>', serve, {'document_root': '/'})
    ]
else:
    # Installed to domain root, without a path prefix
    # Just use the default project urls.py
    from ultimate_ladder.urls import urlpatterns  # noqa

    # TODO: Serve from nginx server ;)
    urlpatterns.append(path('<path:path>', serve, {'document_root': '/'}))
