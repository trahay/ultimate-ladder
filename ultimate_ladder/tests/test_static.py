"""Tests of the static files (CSS), which must be served also when DEBUG is
False, as in production."""
import hashlib

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from ultimate_ladder.templatetags.static_version import file_version


class StaticFilesTests(TestCase):
    def test_debug_is_false_in_tests(self):
        from django.conf import settings
        self.assertFalse(settings.DEBUG)

    def test_stylesheet_is_served(self):
        response = self.client.get("/static/ultimate_ladder/style.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"language-selector", b"".join(response.streaming_content))

    def test_admin_static_files_are_served(self):
        response = self.client.get("/static/admin/css/base.css")
        self.assertEqual(response.status_code, 200)

    def test_stylesheet_url_has_a_version(self):
        with open(finders.find("ultimate_ladder/style.css"), "rb") as f:
            version = hashlib.md5(f.read()).hexdigest()[:10]
        self.assertEqual(file_version("ultimate_ladder/style.css"), version)
        response = self.client.get(reverse("login"))
        self.assertContains(response, f'href="/static/ultimate_ladder/style.css?v={version}"')

    def test_unknown_file_has_no_version(self):
        self.assertIsNone(file_version("does/not/exist.css"))
