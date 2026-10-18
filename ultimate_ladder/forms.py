from django.db import models
from django import forms
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from .models import Player, League, Game

from django.contrib.auth import get_user_model

User = get_user_model()

class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = '__all__'


class PlayerEditForm(forms.ModelForm):
    """Form to create or edit a player."""
    class Meta:
        model = Player
        fields = ['name', 'gender', 'initial_score']
        labels = {
            'name': _('Name'),
            'gender': _('Gender'),
            'initial_score': _('Initial score'),
        }
        help_texts = {
            'initial_score': _('Estimated level of the player when they join: 1000 for an average player. '
                               'Their score then evolves with the results of their games.'),
        }


class LeagueForm(forms.ModelForm):
    """Form to create or edit a league."""
    class Meta:
        model = League
        fields = ['name']
        labels = {'name': _('Name')}


ALL_PLAYERS=Player.objects.all().values_list('id', 'name')
class GameForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # only print the players of the current user, sorted by name
        owner=User.objects.get(username=kwargs["initial"]["owner"])
        self.fields['players'].queryset = Player.objects.filter(owner=owner).order_by(Lower('name'))

    players = forms.ModelMultipleChoiceField(
                widget = forms.CheckboxSelectMultiple,
                queryset = Player.objects.all(),
                initial = 0
            )

    def clean_players(self):
        if len(self.cleaned_data['players']) < 2:
            raise forms.ValidationError(_('Select at least two players.'))
        return self.cleaned_data['players']


    class Meta:
        model = Game
        fields = ['players']
        

TEAM_CHOICES = [('', _('Absent')), ('A', _('Team A')), ('B', _('Team B'))]

class ManualGameForm(forms.Form):
    """Create a game whose teams are chosen by the user: for each player of
    the owner, choose whether they are absent, in team A or in team B."""

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.players = list(Player.objects.filter(owner=owner).order_by(Lower('name')))
        for player in self.players:
            self.fields[self.field_name(player.id)] = forms.ChoiceField(
                label=player.name,
                choices=TEAM_CHOICES,
                required=False,
                widget=forms.RadioSelect,
            )

    @staticmethod
    def field_name(player_id):
        return f'player_{player_id}'

    def player_fields(self):
        """(player, bound field) for each player, to render the form."""
        return [(player, self[self.field_name(player.id)]) for player in self.players]

    def team(self, team_name):
        return [player for player in self.players
                if self.cleaned_data.get(self.field_name(player.id)) == team_name]

    def clean(self):
        cleaned_data = super().clean()
        if not self.team('A') or not self.team('B'):
            raise forms.ValidationError(_('Each team needs at least one player.'))
        return cleaned_data


class ScoreForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['score_team_a', 'score_team_b']
        labels = {
            'score_team_a': _('Score of team A'),
            'score_team_b': _('Score of team B')
        }

