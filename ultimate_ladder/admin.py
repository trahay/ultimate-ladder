from django.contrib import admin

# Register your models here.


from .models import Player, League, Game, Team

admin.site.register(Player)
admin.site.register(League)
admin.site.register(Game)
admin.site.register(Team)
