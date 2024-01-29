from django.db import models
from django import forms
from .models import Player, Game

class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = '__all__'


ALL_PLAYERS=Player.objects.all().values_list('id', 'name')
class GameForm(forms.ModelForm):
    players = forms.ModelMultipleChoiceField(
        widget = forms.CheckboxSelectMultiple,
        queryset = Player.objects.all(),
        initial = 0
        )

    def clean_players(self):
        if len(self.cleaned_data['players']) < 2:
            raise forms.ValidationError('Select at least two players.')
        return self.cleaned_data['players']

    class Meta:
        model = Game
        fields = ['players']


class ScoreForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['score_team_a', 'score_team_b']
        labels = {
            'score_team_a': 'Score team A',
            'score_team_b': 'Score team B'
        }

