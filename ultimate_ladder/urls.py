"""
URL configuration for ultimate_ladder project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from . import views

app_name = "ultimate_ladder"

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", views.Index.as_view(), name="index"),
# view players
    path("players/", views.PlayerList.as_view(), name="players"),

#### Player
    path("players/<int:pk>/", views.PlayerDetail.as_view(), name="player"),
    path("players/create/", views.PlayerCreate.as_view(), name="add-player"),
    path("players/edit/<int:pk>", views.PlayerUpdate.as_view(), name="edit-player"),
    path("players/delete/<int:pk>", views.PlayerDelete.as_view(), name="delete-player"),

# view leagues
    path("leagues/", views.LeagueList.as_view(), name="leagues"),
# League
    path("leagues/<int:pk>/", views.LeagueDetail.as_view(), name="league"),
    path("leagues/create/", views.LeagueCreate.as_view(), name="add-league"),
    path("leagues/edit/<int:pk>", views.LeagueUpdate.as_view(), name="edit-league"),
    path("leagues/delete/<int:pk>", views.LeagueDelete.as_view(), name="delete-league"),

# view game
    path("leagues/<int:league_id>/<int:pk>", views.GameDetail.as_view(), name="game"),
# new game
    path("leagues/<int:league_pk>/create_game/", views.NewGame, name="add-game"),
# edit game
    path("leagues/<int:league_id>/delete_game/<int:pk>", views.GameDelete.as_view(), name="delete-game"),
]
