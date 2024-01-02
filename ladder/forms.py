from django.db import models
from django import forms
from .models import Player, Game

class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = '__all__'

ALL_PLAYERS=Player.objects.all().values_list('id', 'name');

class GameForm(forms.ModelForm):
    players = forms.MultipleChoiceField(required=True,
                                        widget = forms.CheckboxSelectMultiple,
                                        choices = ALL_PLAYERS)
    class Meta:
        model = Game
        fields = ['players']

class ScoreForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['score_team_a', 'score_team_b']

