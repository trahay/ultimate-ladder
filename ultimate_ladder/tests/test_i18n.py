"""Tests of the French / English versions of the site."""
import ast
import datetime
import gettext
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .utils import PASSWORD, make_game, make_league, make_player, make_user

LOCALE_DIR = Path(settings.BASE_DIR) / 'locale'


@override_settings(LANGUAGE_CODE='fr')  # as in production (the tests run in English)
class LanguageTests(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        self.url = reverse("index", kwargs={"owner": "alice"})

    def switch_to(self, language):
        return self.client.post(reverse("set_language"), {"language": language, "next": self.url})

    def test_french_by_default(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<html lang="fr">')
        self.assertContains(response, "Ligues")
        self.assertEqual(response.headers["Content-Language"], "fr")

    def test_the_language_of_the_browser_is_ignored(self):
        response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")
        self.assertContains(response, "Ligues")

    def test_switch_to_english_and_back(self):
        response = self.switch_to("en")
        self.assertRedirects(response, self.url)
        response = self.client.get(self.url)
        self.assertContains(response, '<html lang="en">')
        self.assertContains(response, "Leagues")
        self.assertNotContains(response, "Ligues")
        self.switch_to("fr")
        self.assertContains(self.client.get(self.url), "Ligues")

    def test_unknown_language_falls_back_to_french(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "de"
        self.assertContains(self.client.get(self.url), "Ligues")

    def test_language_selector(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="language" value="fr"')
        self.assertContains(response, 'name="language" value="en"')
        # flags, named in their own language
        self.assertContains(response, 'class="flag"', count=2)
        self.assertContains(response, 'aria-label="Français"')
        self.assertContains(response, 'aria-label="English"')
        selector = response.content.decode().split('class="language-selector"')[1]
        self.assertRegex(selector, r'value="fr"[^>]*aria-current="true"')
        self.assertNotRegex(selector, r'value="en"[^>]*aria-current="true"')

    def test_login_page_in_french(self):
        self.client.logout()
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Mot de passe")

    def test_dates_and_plurals(self):
        league = make_league(self.user, "Ligue")
        players = [make_player(self.user, f"P{i}", "f") for i in range(2)]
        game = make_game(league, players[:1], players[1:])
        game.creation_date = datetime.datetime(2026, 10, 18, 12, 25, tzinfo=datetime.timezone.utc)
        game.save()
        response = self.client.get(reverse("game", kwargs={"owner": "alice", "league_id": league.pk, "pk": game.pk}))
        self.assertContains(response, "Match du 18 oct. 2026, 12:25")
        self.assertContains(response, "1 joueur · 1 femme")
        response = self.client.get(reverse("league", kwargs={"owner": "alice", "pk": league.pk}))
        self.assertContains(response, "2 joueurs")
        self.switch_to("en")
        response = self.client.get(reverse("game", kwargs={"owner": "alice", "league_id": league.pk, "pk": game.pk}))
        self.assertContains(response, "Game of Oct 18, 2026, 12:25")

    def test_messages_and_form_errors(self):
        response = self.client.post(reverse("add-player", kwargs={"owner": "alice"}),
                                    {"name": "Eve", "gender": "f", "initial_score": 1000}, follow=True)
        self.assertContains(response, "Le joueur a été créé.")
        self.assertContains(self.client.get(reverse("add-player", kwargs={"owner": "alice"})), "Niveau initial")
        league = make_league(self.user)
        alone = make_player(self.user, "Alone")
        response = self.client.post(reverse("add-game", kwargs={"owner": "alice", "league_pk": league.pk}),
                                    {"players": [alone.pk]})
        self.assertContains(response, "Sélectionnez au moins deux joueurs.")

    def test_tables_are_translated(self):
        make_player(self.user, "Bob")
        response = self.client.get(reverse("players", kwargs={"owner": "alice"}))
        self.assertContains(response, "i18n/fr-FR.json")
        self.switch_to("en")
        response = self.client.get(reverse("players", kwargs={"owner": "alice"}))
        self.assertNotContains(response, "i18n/fr-FR.json")


def parse_po(path):
    """{(context, msgid): msgstr or [msgstr plural forms]} of a .po file
    (minimal parser, enough for the files generated by makemessages)."""
    entries, entry, key = {}, {}, None

    def flush():
        if 'msgid' in entry and entry['msgid']:
            if 'msgid_plural' in entry:
                value = [entry[k] for k in sorted(k for k in entry if k.startswith('msgstr['))]
            else:
                value = entry.get('msgstr', '')
            entries[(entry.get('msgctxt'), entry['msgid'])] = (value, entry.get('fuzzy', False))
        entry.clear()

    for line in Path(path).read_text().splitlines() + ['']:
        if not line.strip():
            flush()
        elif line.startswith('#,') and 'fuzzy' in line:
            entry['fuzzy'] = True
        elif line.startswith('#'):
            continue
        elif line.startswith('"'):
            entry[key] += ast.literal_eval(line)
        else:
            key, value = line.split(' ', 1)
            entry[key] = ast.literal_eval(value)
    return entries


class CatalogTests(SimpleTestCase):
    po_file = LOCALE_DIR / 'fr' / 'LC_MESSAGES' / 'django.po'
    mo_file = LOCALE_DIR / 'fr' / 'LC_MESSAGES' / 'django.mo'

    def test_everything_is_translated(self):
        for (context, msgid), (msgstr, fuzzy) in parse_po(self.po_file).items():
            with self.subTest(msgid=msgid):
                self.assertFalse(fuzzy)
                if isinstance(msgstr, list):
                    self.assertTrue(all(msgstr))
                else:
                    self.assertTrue(msgstr)

    def test_compiled_catalog_is_up_to_date(self):
        """The .mo file must be regenerated (compilemessages) after each
        change of the .po file."""
        with open(self.mo_file, 'rb') as f:
            catalog = gettext.GNUTranslations(f)
        for (context, msgid), (msgstr, fuzzy) in parse_po(self.po_file).items():
            with self.subTest(msgid=msgid):
                if isinstance(msgstr, list):
                    self.assertEqual(catalog.npgettext(context, msgid, msgid + 's', 1) if context
                                     else catalog.ngettext(msgid, msgid + 's', 1), msgstr[0])
                elif context:
                    self.assertEqual(catalog.pgettext(context, msgid), msgstr)
                else:
                    self.assertEqual(catalog.gettext(msgid), msgstr)
