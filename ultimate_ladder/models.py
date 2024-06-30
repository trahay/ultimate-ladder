from django.db import models
import datetime
#import settings
from django.utils import timezone
from django.conf import settings

# Create your models here.
genders=( ('m', 'M'), ('f', 'F'))

class Player(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False)
    name = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, choices=genders)
    score = models.IntegerField(default=1000)
    def __str__(self):
        return self.name + " (" + self.gender + ")"
    def value(self):
        return (self.id, self.name)
    
class League(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False)
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name

class Game(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    creation_date = models.DateTimeField()
    completion_date = models.DateTimeField(default=datetime.datetime.utcfromtimestamp(0))
    completed = models.BooleanField(default=False)
    score_team_a = models.IntegerField(default=0)
    score_team_b = models.IntegerField(default=0)
    def __str__(self):
        return str(self.league) + " ("+str(self.creation_date)+")"

class Team(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    team_name = models.CharField(max_length=1)
    def __str__(self):
        return str(self.player) + " ("+str(self.game)+" / "+self.team_name+")" + "(db:"+str(self.owner)+")"

class PlayerStats(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    win = models.IntegerField(default=0)
    loss = models.IntegerField(default=0)
    draw = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    
    
