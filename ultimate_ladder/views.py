from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormMixin
from django.views.generic.base import RedirectView
from django.contrib import messages
from datetime import datetime
from django.db.models import Count
import pandas as pd
import sys
import math
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

User = get_user_model()


sys.path.insert(0, './ultimate_ladder/matchmaking')
import matchmaking as mm


import logging
logger = logging.getLogger(__name__)

from .forms import PlayerForm, GameForm, ScoreForm
from .models import Player, League, Game, Team, PlayerStats


def getUserDB(username):
    return User.objects.get(username=username)

class IndexRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = "index"

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return reverse('ultimate_ladder:index', kwargs={"owner": self.request.user})
        else:
            return reverse('ultimate_ladder:login')


class Index(generic.ListView):
    model=League
    context_object_name = "league_list"
    template_name = "ultimate_ladder/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owner=getUserDB(self.kwargs["owner"])
        context["owner"]=owner.username
        context["all_players"]=Player.objects.filter(owner=owner)
        context["league_list"]=League.objects.filter(owner=owner)
        return context


class PlayerList(generic.ListView):
    model=Player
    context_object_name = "player_list"
    template_name = "ultimate_ladder/players.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owner=getUserDB(self.kwargs["owner"])
        context["owner"]=owner.username
        context["player_list"]=Player.objects.filter(owner=owner)
        return context

class PlayerDetail(generic.DetailView):
    model=Player
    template_name = "ultimate_ladder/player.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owner=getUserDB(self.kwargs["owner"])
        context["owner"]=owner.username
        context["form"] = PlayerForm()
        return context


class LeagueList(generic.ListView):
    model=League
    context_object_name = "league_list"
    template_name = "ultimate_ladder/leagues.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user=User.objects.get(username=self.kwargs["owner"])
        context["owner"]=self.kwargs["owner"]
        context["league_list"]=League.objects.filter(owner=user)
        return context

class LeagueDetail(generic.DetailView):
    model=League
    template_name = "ultimate_ladder/league.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ongoing_games"] = context["league"].game_set.filter(completed=False)
        context["completed_games"] = context["league"].game_set.filter(completed=True)
        context["player_list"] = context["league"].playerstats_set.all()

        return context

# require authentification
class PlayerCreate(LoginRequiredMixin, CreateView):
    model = Player
    fields = [ 'name', 'gender', 'score' ]
    template_name = "ultimate_ladder/edit_player.html"

    def get_success_url(self):
        return reverse('ultimate_ladder:players', kwargs={"owner": self.request.user})

    def form_valid(self, form, **kwargs):
        messages.success(self.request, "The Player was created successfully.")
        name=form.cleaned_data.get("name")
        gender=form.cleaned_data.get("gender")
        score=form.cleaned_data.get("score")
        if self.request.user.is_authenticated:
            owner=self.request.user
        user_name=owner.username
        form.instance.owner=owner
        logger.warning("PlayerCreate(userdb='"+str(user_name)+"', name='"+name+"', gender='"+gender+"', score='"+str(score)+"')")

        return super(PlayerCreate, self).form_valid(form)

class PlayerUpdate(LoginRequiredMixin, UpdateView):
    model = Player
    fields = [ 'name', 'gender', 'score' ]
    template_name = "ultimate_ladder/edit_player.html"

    def get_success_url(self):
        return reverse('ultimate_ladder:players', kwargs={"owner": self.request.user})

    # make sure a user only modifies its data !
    def get_object(self, *args, **kwargs):
        obj = super(PlayerUpdate, self).get_object(*args, **kwargs)
        if not obj.owner == self.request.user:
            raise Http404
        return obj

    def form_valid(self, form):
        messages.success(self.request, "The Player was updated successfully.")
        name=form.cleaned_data.get("name")
        gender=form.cleaned_data.get("gender")
        score=form.cleaned_data.get("score")
        owner=self.request.user
        logger.warning("PlayerUpdate(name='"+name+"', gender='"+gender+"', score='"+str(score)+"')")
        return super(PlayerUpdate,self).form_valid(form)

class PlayerDelete(LoginRequiredMixin, DeleteView):
    model = Player
    context_object_name = 'player'
    def get_success_url(self):
        return reverse('ultimate_ladder:players', kwargs={"owner": self.request.user})
    
    # make sure a user only modifies its data !
    def get_object(self, *args, **kwargs):
        obj = super(PlayerDelete, self).get_object(*args, **kwargs)
        if not obj.owner == self.request.user:
            raise Http404
        return obj

    def form_valid(self, form):
        messages.success(self.request, "The Player was deleted successfully.")
        name=form.cleaned_data.get("name")
        logger.warning("PlayerDeleteUpdate()")
        return super(PlayerDelete,self).form_valid(form)



class LeagueCreate(LoginRequiredMixin, CreateView):
    model = League
    fields = [ 'name' ]
    template_name = "ultimate_ladder/edit_league.html"

    def get_success_url(self):
        return reverse('ultimate_ladder:leagues', kwargs={"owner": self.request.user})

    def form_valid(self, form):
        messages.success(self.request, "The League was created successfully.")
        name=form.cleaned_data.get("name")
        if self.request.user.is_authenticated:
            owner=self.request.user
        user_name=owner.username
        form.instance.owner=owner

        logger.warning("LeagueCreate(name='"+name+"')")
        return super(LeagueCreate,self).form_valid(form)

class LeagueUpdate(LoginRequiredMixin, UpdateView):
    model = League
    fields = [ 'name' ]
    template_name = "ultimate_ladder/edit_league.html"

    def get_success_url(self):
        return reverse('ultimate_ladder:leagues', kwargs={"owner": self.request.user})

    # make sure a user only modifies its data !
    def get_object(self, *args, **kwargs):
        obj = super(LeagueUpdate, self).get_object(*args, **kwargs)
        if not obj.owner == self.request.user:
            raise Http404
        return obj

    def form_valid(self, form):
        messages.success(self.request, "The League was updated successfully.")
        logger.warning("LeagueUpdate(name='"+form.instance.name+"')")
        return super(LeagueUpdate,self).form_valid(form)

class LeagueDelete(LoginRequiredMixin, DeleteView):
    model = League
    context_object_name = 'league'

    def get_success_url(self):
        return reverse('ultimate_ladder:leagues', kwargs={"owner": self.request.user})
    
    # make sure a user only modifies its data !
    def get_object(self, *args, **kwargs):
        obj = super(LeagueDelete, self).get_object(*args, **kwargs)
        if not obj.owner == self.request.user:
            raise Http404
        return obj

    def form_valid(self, form):
        messages.success(self.request, "The League was deleted successfully.")
        logger.warning("LeagueDelete()")
        return super(LeagueDelete,self).form_valid(form)

def get_team_score(owner, Game, team_name):
    team=Game.team_set.filter(team_name=team_name, owner=owner)
    logger.warning("team:"+str(team))
    return TeamScore(team)


class GameDetail(FormMixin, generic.DetailView):
    model=Game
    template_name = "ultimate_ladder/game.html"
    form_class=ScoreForm

    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        owner=getUserDB(self.kwargs["owner"])
        context["owner"]=owner.username
        context["score_team_a"] = get_team_score(owner, context["game"], 'A')
        context["score_team_b"] = get_team_score(owner, context["game"], 'B')
        context["team_a"] = context["game"].team_set.filter(team_name='A')
        context["team_b"] = context["game"].team_set.filter(team_name='B')
        context["league"] = context["game"].league
        return context

    def post(self, *args, **kwargs):
        league = get_object_or_404(League, id=kwargs.get("league_id"))
        game = get_object_or_404(Game, id=kwargs.get("pk"))
        form = self.get_form()

        if not game.owner == self.request.user:
            messages.error(self.request, "You can only modify you own games !")
            raise Http404

        if form.is_valid():    
            if game.completed == True:
                messages.error(self.request, "The Game is already completed.")
                return HttpResponseRedirect(reverse('ultimate_ladder:game', kwargs={"owner":league.owner, "league_id":league.id, "pk":game.id}))

            game.score_team_a = form.cleaned_data.get("score_team_a")
            game.score_team_b = form.cleaned_data.get("score_team_b")
            game.completed = True
            game.completion_date = datetime.now()
            game.save()
            logger.warning("GameComplete(game='"+str(game)+"', score="+str(game.score_team_a)+"-"+str(game.score_team_b)+")")

            UpdateStats(game)

            messages.success(self.request, "The Game was updated successfully.")
            return HttpResponseRedirect(reverse('ultimate_ladder:league', kwargs={"owner": league.owner, "pk":league.id}))
        messages.error(request, "form is not valid!.")
        return HttpResponseRedirect(reverse('ultimate_ladder:game', kwargs={"owner": league.owner, "league_id":league.id, "pk":game.id}))


class GameDelete(LoginRequiredMixin, DeleteView):
    model = Game
    context_object_name = 'game'

    def get_success_url(self):
        return reverse('ultimate_ladder:leagues', kwargs={"owner": self.request.user})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["league"] = context["game"].league
        return context

    def get_object(self, *args, **kwargs):
        obj = super(GameDelete, self).get_object(*args, **kwargs)
        if not obj.owner == self.request.user:
            raise Http404
        return obj

    def form_valid(self, form):
        messages.success(self.request, "The Game was deleted successfully.")
        game=form.cleaned_data.get("game")
        logger.warning("GameDelete()")
        return super(GameDelete,self).form_valid(form)


@login_required
def NewGame(request, league_pk, owner):
    user=getUserDB(owner)
    league = get_object_or_404(League, id=league_pk, owner=user)
    if request.method == 'GET':
        context = {'form': GameForm(instance=league), 'league': league, 'owner': owner}
        return render(request,'ultimate_ladder/new_game.html',context)
    elif request.method == 'POST':
        form = GameForm(request.POST)

        if not league.owner == request.user:
            messages.error(request, "You can only modify create game for your own league !")
            raise Http404

        if form.is_valid():
            game = Game(league=league,
                        creation_date=datetime.now(),
                        owner=league.owner)
            game.save()
            players = form.cleaned_data.get("players")

            nb_players=len(players)
            print(str(nb_players) + " Players:"+str(players))

            # Matchmaking algorithm:
            # for each gender, make 2 teams with similar score
            # Then, concatenate the genders
            player_list_m=[]
            skill_list_m=[]
            player_list_f=[]
            skill_list_f=[]
            # take the list of players along with their score
            for p in players:
                if p.gender == 'm':
                    player_list_m.append(p.id)
                    skill_list_m.append(p.score)
                else:
                    player_list_f.append(p.id)
                    skill_list_f.append(p.score)

            d_m={'player': player_list_m, 'skill': skill_list_m}
            df_m = pd.DataFrame(data=d_m)
            d_f={'player': player_list_f, 'skill': skill_list_f}
            df_f = pd.DataFrame(data=d_f)
            # Call a matchmaking algorithm
            team_a_players_m=[]
            team_a_players_f=[]
            team_b_players_m=[]
            team_b_players_f=[]
            if len(player_list_m) > 0:
                my_mm_m = mm.MatchMaking(df_m, teamsize=math.ceil(len(player_list_m)/2))
                teams_m=my_mm_m.optimize()

                team_a_id=min(teams_m["team"])
                team_b_id=max(teams_m["team"])

                # get the results of the matchmaking
                team_a_players_m = list(teams_m[teams_m["team"]==team_a_id]["player"])
                team_b_players_m = list(teams_m[teams_m["team"]==team_b_id]["player"])

                logger.warning("Team A is team #"+str(team_a_id)+". Player list: "+str(team_a_players_m))
                logger.warning("Team B is team #"+str(team_b_id)+". Player list: "+str(team_b_players_m))

            if len(player_list_f) > 0:
                my_mm_f = mm.MatchMaking(df_f, teamsize=math.ceil(len(player_list_f)/2))
                teams_f=my_mm_f.optimize()
                team_a_id=min(teams_f["team"])
                team_b_id=max(teams_f["team"])
                # get the results of the matchmaking
                team_a_players_f = list(teams_f[teams_f["team"]==team_a_id]["player"])
                team_b_players_f = list(teams_f[teams_f["team"]==team_b_id]["player"])
                logger.warning("Team A is team #"+str(team_a_id)+". Player list: "+str(team_a_players_f))
                logger.warning("Team B is team #"+str(team_b_id)+". Player list: "+str(team_b_players_f))

            nb_players_a=len(team_a_players_m)+len(team_a_players_f)
            nb_players_b=len(team_b_players_m)+len(team_b_players_f)
            if nb_players_a > nb_players_b + 1 or  nb_players_b > nb_players_a + 1 :
                # imbalance. This is because there's an odd number of
                # male, and an odd number of female. As a result, the
                # matchmaking algorithm assigns 2 more players in one
                # team.

                # Solution: swap the female teams
                temp=team_a_players_f
                team_a_players_f = team_b_players_f 
                team_b_players_f = temp
                logger.warning("Imbalance detected. Swapping team_f_a and team_f_b")

            team_a=[]
            team_b=[]
            # Create Team entries in the database
            for p in team_a_players_m + team_a_players_f:
                player = get_object_or_404(Player, id=p)
                logger.warning("Adding "+str(player)+" to team A")
                t = Team(game=game, player=player, team_name='A', owner=league.owner)
                t.save()
                team_a.append(player)

            for p in team_b_players_m + team_b_players_f:
                player = get_object_or_404(Player, id=p)
                logger.warning("Adding "+str(player)+" to team B")
                t = Team(game=game, player=player, team_name='B', owner=league.owner)
                t.save()
                team_b.append(player)

            logger.warning("NewGame(game='"+str(game)+"', team_a="+str(team_a)+", team_b="+str(team_b)+")")
            return HttpResponseRedirect(reverse('ultimate_ladder:game', kwargs={"league_id":league.id, "pk":game.id, "owner":owner}))
        else:
            context = {'form': form, 'league': league, "owner": owner}
            return render(request, 'ultimate_ladder/new_game.html', context)

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

        playerStat,created = PlayerStats.objects.get_or_create(player=p, league=game.league, owner=game.owner)
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

        playerStat,created = PlayerStats.objects.get_or_create(player=p, league=game.league, owner=game.owner)
        if(game.score_team_b > game.score_team_a):
            playerStat.win = playerStat.win + 1
        if(game.score_team_b == game.score_team_a):
            playerStat.draw = playerStat.draw + 1
        if(game.score_team_b < game.score_team_a):
            playerStat.loss = playerStat.loss + 1
        playerStat.total_points = playerStat.total_points - team_a_points
        playerStat.save()

