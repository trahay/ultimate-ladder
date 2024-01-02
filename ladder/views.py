from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormMixin
from django.contrib import messages
from datetime import datetime    

from .forms import PlayerForm, GameForm, ScoreForm
from .models import Player, League, Game, Team


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
        return super(PlayerCreate,self).form_valid(form)

class PlayerUpdate(UpdateView):
    model = Player
    fields = [ 'name', 'gender', 'score' ]
    success_url = reverse_lazy("ladder:players")
    template_name = "ladder/edit_player.html"
    def form_valid(self, form):
        messages.success(self.request, "The Player was updated successfully.")
        return super(PlayerUpdate,self).form_valid(form)

class PlayerDelete(DeleteView):
    model = Player
    context_object_name = 'player'
    success_url = reverse_lazy("ladder:players")
    
    def form_valid(self, form):
        messages.success(self.request, "The Player was deleted successfully.")
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
        return context

class LeagueCreate(CreateView):
    model = League
    fields = [ 'name' ]
    success_url = reverse_lazy("ladder:leagues")
    template_name = "ladder/edit_league.html"

    def form_valid(self, form):
        messages.success(self.request, "The League was created successfully.")
        return super(LeagueCreate,self).form_valid(form)

class LeagueUpdate(UpdateView):
    model = League
    fields = [ 'name' ]
    success_url = reverse_lazy("ladder:league")
    template_name = "ladder/edit_league.html"
    def form_valid(self, form):
        messages.success(self.request, "The League was updated successfully.")
        return super(LeagueUpdate,self).form_valid(form)

class LeagueDelete(DeleteView):
    model = League
    context_object_name = 'league'
    success_url = reverse_lazy("ladder:leagues")
    
    def form_valid(self, form):
        messages.success(self.request, "The League was deleted successfully.")
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
            for p in team_a_players:
                player = get_object_or_404(Player, id=p)
                t = Team(game=game, player=player, team_name='A')
                t.save()
            for p in team_b_players:
                player = get_object_or_404(Player, id=p)
                t = Team(game=game, player=player, team_name='B')
                t.save()

            return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))
        else:
            return render(request, 'ladder/new_game.html', {'form': form})

def UpdateStats(game):
    delta=(game.score_team_a - game.score_team_b) * 10
    for t in game.team_set.filter(team_name='A'):
        p = t.player
        p.score = p.score + delta
        p.save()       

    for t in game.team_set.filter(team_name='B'):
        p = t.player
        p.score = p.score - delta
        p.save()

def EditGame(request, league_id, pk):
    league = get_object_or_404(League, id=league_id)
    game = get_object_or_404(Game, id=pk)
    if request.method == 'POST':
        form = ScoreForm(request.POST)
        if form.is_valid():    
            if game.completed == True:
                messages.error(request, "The Game is already completed.")
                return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))

            game.completed = True
            game.completion_date = datetime.now()
            game.save()
            UpdateStats(game)

            messages.success(request, "The Game was updated successfully.")
            return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))
        else:
            messages.error(request, "form is not valid!.")
    else:
        messages.error(request, "method != post")
    return HttpResponseRedirect(reverse('ladder:game', kwargs={"league_id":league.id, "pk":game.id}))
