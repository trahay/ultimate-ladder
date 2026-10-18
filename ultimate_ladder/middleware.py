from django.conf import settings
from django.utils import translation
from django.utils.cache import patch_vary_headers


class LanguageMiddleware:
    """Select the language of the site: the one chosen by the user with the
    language selector (stored in a cookie by the set_language view), or the
    default language (settings.LANGUAGE_CODE).

    Unlike django.middleware.locale.LocaleMiddleware, the language of the
    browser is not used: the site is in French unless the user selects
    another language."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if language not in dict(settings.LANGUAGES):
            language = settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
        response = self.get_response(request)
        patch_vary_headers(response, ('Cookie',))
        response.headers.setdefault('Content-Language', language)
        return response
