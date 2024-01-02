from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormMixin
from django.contrib import messages
from datetime import datetime
from django.db.models import Count

import logging
logger = logging.getLogger(__name__)

from .forms import PlayerForm, GameForm, ScoreForm
from .models import Player, League, Game, Team, PlayerStats


class Index(generic.ListView):
    model=League
    context_object_name = "league_list"
    template_name = "ladder/index.html"
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context["all_players"]=Player.objects.all()
        return context


class PlayerList(generic.ListView):
    model=Player
    context_object_name = "player_list"
    template_name = "ladder/players.html"

class PlayerDetail(generic.DetailView):
    model=Player
    template_name = "ladder/player.html"
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context["form"] = PlayerForm()
        return context

class PlayerCreate(CreateView):
    model = Player
    fields = [ 'name', 'gender', 'score' ]
    success_url = reverse_lazy("ladder:players")
    template_name = "ladder/edit_player.html"

    def form_valid(self, form):
        messages.success(self.request, "The Player was created successfully.")
        name=form.cleaned_data.get("name")
        gender=form.cleaned_data.get("gender")
        score=form.cleaned_data.get("score")
        logger.warning("PlayerCreate(name='"+name+"', gender='"+gender+"', score='"+str(score)+"')")

        return super(PlayerCreate,self).form_valid(form)

class PlayerUpdate(UpdateView):
    model = Player
    fields = [ 'name', 'gender', 'score' ]
    success_url = reverse_lazy("ladder:players")
    template_name = "ladder/edit_player.html"
    def form_valid(self, form):
        messages.success(self.request, "The Player was updated successfully.")
        name=form.cleaned_data.get("name")
        gender=form.cleaned_data.get("gender")
        score=form.cleaned_data.get("score")
        logger.warning("PlayerUpdate(name='"+name+"', gender='"+gender+"', score='"+str(score)+"')")
        return super(PlayerUpdate,self).form_valid(form)

class PlayerDelete(DeleteView):
    model = Player
    context_object_name = 'player'
    success_url = reverse_lazy("ladder:players")
    
    def form_valid(self, form):
        messages.success(self.request, "The Player was deleted successfully.")
        name=form.cleaned_data.get("name")
        logger.warning("PlayerDeleteUpdate()")
        return super(PlayerDelete,self).form_valid(form)


class LeagueList(generic.ListView):
    model=League
    context_object_name = "league_list"
    template_name = "ladder/leagues.html"

class LeagueDetail(generic.DetailView):
    model=League
    template_name = "ladder/league.html"
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context["ongoing_games"] = context["league"].game_set.filter(completed=False)
        context["completed_games"] = context["league"].game_set.filter(completed=True)
        context["player_list"] = context["league"].playerstats_set.all()

        return context

class LeagueCreate(CreateView):
    model = League
    fields = [ 'name' ]
    success_url = reverse_lazy("ladder:leagues")
    template_name = "ladder/edit_league.html"

    def form_valid(self, form):
        messages.success(self.request, "The League was created successfully.")
        name=form.cleaned_data.get("name")
        logger.warning("LeagueCreate(name='"+name+"')")
        return super(LeagueCreate,self).form_valid(form)

class LeagueUpdate(UpdateView):
    model = League
    fields = [ 'name' ]
    success_url = reverse_lazy("ladder:league")
    template_name = "ladder/edit_league.html"
    def form_valid(self, form):
        messages.success(self.request, "The League was updated successfully.")
        logger.warning("LeagueUpdate(name='"+name+"')")
        return super(LeagueUpdate,self).form_valid(form)

class LeagueDelete(DeleteView):
    model = League
    context_object_name = 'league'
    success_url = reverse_lazy("ladder:leagues")
    
    def form_valid(self, form):
        messages.success(self.request, "The League was deleted successfully.")
        logger.warning("LeagueDelete()")
        return super(LeagueDelete,self).form_valid(form)

    
class GameDetail(FormMixin, generic.DetailView):
    model=Game
    template_name = "ladder/game.html"
    form_class=ScoreForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["team_a"] = context["game"].team_set.filter(team_name='A')
        context["team_b"] = context["game"].team_set.filter(team_name='B')
        context["league"] = context["game"].league
        return context
    def post(self, request, *args, **kwargs):
        league = get_object_or_404(League, id=kwargs.get("league_id"))
        game = get_object_or_404(Game, id=kwargs.get("pk"))
        form = self.get_form()
        if form.is_valid():    
            if game.completed == True:
                messages.error(request, "The Game is already completed.")
                return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))

            game.score_team_a = form.cleaned_data.get("score_team_a")
            game.score_team_b = form.cleaned_data.get("score_team_b")
            game.completed = True
            game.completion_date = datetime.now()
            game.save()
            logger.warning("GameComplete(game='"+str(game)+"', score="+str(game.score_team_a)+"-"+str(game.score_team_b)+")")

            UpdateStats(game)

            messages.success(request, "The Game was updated successfully.")
            return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))
        messages.error(request, "form is not valid!.")
        return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))


class GameDelete(DeleteView):
    model = Game
    context_object_name = 'game'
    success_url = reverse_lazy("ladder:leagues")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["league"] = context["game"].league
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "The Game was deleted successfully.")
        game=form.cleaned_data.get("game")
        logger.warning("GameDelete()")
        return super(GameDelete,self).form_valid(form)


def NewGame(request, league_id):
    league = get_object_or_404(League, id=league_id)
    if request.method == 'GET':
        context = {'form': GameForm(instance=league), 'league': league}
        return render(request,'ladder/new_game.html',context)
    elif request.method == 'POST':
        form = GameForm(request.POST)
        if form.is_valid():
            game = Game(league=league,
                        creation_date=datetime.now())
            game.save()
            players = form.cleaned_data.get("players")
            # TODO: matchmaking !
            team_a_players = players[:int(len(players)/2)]
            team_b_players = players[int(len(players)/2):]
            team_a=[]
            team_b=[]
            for p in team_a_players:
                player = get_object_or_404(Player, id=p)
                t = Team(game=game, player=player, team_name='A')
                t.save()
                team_a.append(player)

            for p in team_b_players:
                player = get_object_or_404(Player, id=p)
                t = Team(game=game, player=player, team_name='B')
                t.save()
                team_b.append(player)

            logger.warning("NewGame(game='"+str(game)+"', team_a="+str(team_a)+", team_b="+str(team_b)+")")
            return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))
        else:
            return render(request, 'ladder/new_game.html', {'form': form})

def TeamScore(team):
    score=0
    for t in team:
         player = t.player
         score = score + player.score
    return score

def UpdateStats(game):
    # We need to update each player's score

    # The winning team's players score increase, and the loosers score decrease
    # The sum of increase and decrease should be zero
    # (actually there's a rounding error, so it may not be exactly zero)

    nb_players=game.team_set.count()
    # On average, each player will get 5 points for each point difference during this game
    delta=(game.score_team_a - game.score_team_b) * 5 * nb_players

    # Then, if a team is "stronger" than the other, reduce/increase the delta
    score_a=TeamScore(game.team_set.filter(team_name='A'))
    score_b=TeamScore(game.team_set.filter(team_name='B'))
    team_balance=score_a/score_b
    delta=delta*team_balance
    
    # The number of players may be different
    # This is the number of points to give/remove to each team
    nb_points=delta*nb_players/2
    team_a_points=nb_points/game.team_set.filter(team_name='A').count()
    team_b_points=nb_points/game.team_set.filter(team_name='B').count()

    logger.warning("UpdateStats(game='"+str(game)+"', level_a="+str(score_a)+", level_b="+str(score_b)+")")
    
    logger.warning("UpdateStats(game='"+str(game)+"', score="+str(game.score_team_a)+"-"+str(game.score_team_b)+", delta="+str(delta)+")")

    
    for t in game.team_set.filter(team_name='A'):
        p = t.player
        new_score=p.score + team_a_points
        logger.warning("\tUpdateStats(player='"+str(p)+"', score="+str(p.score)+") -> "+str(new_score))
        p.score = new_score        
        p.save()

        playerStat,created = PlayerStats.objects.get_or_create(player=p, league=game.league)
        if(game.score_team_a > game.score_team_b):
            playerStat.win = playerStat.win + 1
        if(game.score_team_a == game.score_team_b):
            playerStat.draw = playerStat.draw + 1
        if(game.score_team_a < game.score_team_b):
            playerStat.loss = playerStat.loss + 1
        playerStat.total_points = playerStat.total_points + team_a_points
        playerStat.save()

    for t in game.team_set.filter(team_name='B'):
        p = t.player
        new_score=p.score - team_b_points
        logger.warning("\tUpdateStats(player='"+str(p)+"', score="+str(p.score)+") -> "+str(new_score))
        p.score = new_score
        p.save()

        playerStat,created = PlayerStats.objects.get_or_create(player=p, league=game.league)
        if(game.score_team_b > game.score_team_a):
            playerStat.win = playerStat.win + 1
        if(game.score_team_b == game.score_team_a):
            playerStat.draw = playerStat.draw + 1
        if(game.score_team_b < game.score_team_a):
            playerStat.loss = playerStat.loss + 1
        playerStat.total_points = playerStat.total_points - team_a_points
        playerStat.save()

#def EditGame(request, league_id, pk):
#    league = get_object_or_404(League, id=league_id)
#    game = get_object_or_404(Game, id=pk)
#    if request.method == 'POST':
#        form = ScoreForm(request.POST)
#        if form.is_valid():    
#            if game.completed == True:
#                messages.error(request, "The Game is already completed.")
#                return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))
#
#            game.completed = True
#            game.completion_date = datetime.now()
#            game.save()
#            logger.warning("NewGame(game='"+str(game)+"', team_a="+str(team_a)+", team_b="+str(team_b)+")")
#
#            UpdateStats(game)
#
#            messages.success(request, "The Game was updated successfully.")
#            return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))
#        else:
#            messages.error(request, "form is not valid!.")
#    else:
#        messages.error(request, "method != post")
#    return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))
#
