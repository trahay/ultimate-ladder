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
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from . import views
from django.views.generic import RedirectView

app_name = "ultimate_ladder"

urlpatterns = [
    path(f'{settings.PATH_URL}/accounts/', include('django.contrib.auth.urls')),
    path(f'{settings.PATH_URL}/admin/', admin.site.urls),

    path(f'{settings.PATH_URL}/', views.IndexRedirectView.as_view(), name="index-redirect"),
    path(f'{settings.PATH_URL}/ultimate_ladder/', views.IndexRedirectView.as_view(), name="index-redirect"),
    path(f'{settings.PATH_URL}/<str:owner>/', views.Index.as_view(), name="index"),

# view players
    path(f'{settings.PATH_URL}/<str:owner>/players/', views.PlayerList.as_view(), name="players"),

#### Player
    path(f'{settings.PATH_URL}/<str:owner>/players/<int:pk>/', views.PlayerDetail.as_view(), name="player"),
    path(f'{settings.PATH_URL}/<str:owner>/players/create/', views.PlayerCreate.as_view(), name="add-player"),
    path(f'{settings.PATH_URL}/<str:owner>/players/edit/<int:pk>', views.PlayerUpdate.as_view(), name="edit-player"),
    path(f'{settings.PATH_URL}/<str:owner>/players/delete/<int:pk>', views.PlayerDelete.as_view(), name="delete-player"),

# view leagues
    path(f'{settings.PATH_URL}/<str:owner>/leagues/', views.LeagueList.as_view(), name="leagues"),
# League
    path(f'{settings.PATH_URL}/<str:owner>/leagues/<int:pk>/', views.LeagueDetail.as_view(), name="league"),
    path(f'{settings.PATH_URL}/<str:owner>/leagues/create/', views.LeagueCreate.as_view(), name="add-league"),
    path(f'{settings.PATH_URL}/<str:owner>/leagues/edit/<int:pk>', views.LeagueUpdate.as_view(), name="edit-league"),
    path(f'{settings.PATH_URL}/<str:owner>/leagues/delete/<int:pk>', views.LeagueDelete.as_view(), name="delete-league"),

# view game
    path(f'{settings.PATH_URL}/<str:owner>/leagues/<int:league_id>/<int:pk>', views.GameDetail.as_view(), name="game"),
# new game
    path(f'{settings.PATH_URL}/<str:owner>/leagues/<int:league_pk>/create_game/', views.NewGame, name="add-game"),
# edit game
    path(f'{settings.PATH_URL}/<str:owner>/leagues/<int:league_id>/delete_game/<int:pk>', views.GameDelete.as_view(), name="delete-game"),
]
