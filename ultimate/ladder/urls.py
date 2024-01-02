from django.urls import path

from . import views

app_name="ladder"
urlpatterns = [
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
    path("leagues/<int:league_id>/create_game/", views.NewGame, name="add-game"),
# edit game
    path("leagues/<int:league_id>/edit_game/<int:pk>", views.EditGame, name="edit-game"),
    path("leagues/<int:league_id>/delete_game/<int:pk>", views.GameDelete.as_view(), name="delete-game"),
]
