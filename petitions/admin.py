from django.contrib import admin
from .models import Petition, PetitionVote

@admin.register(Petition)
class PetitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'director', 'year', 'posted_by', 'created_at', 'votes_count')
    search_fields = ('title', 'director', 'posted_by__username')

@admin.register(PetitionVote)
class PetitionVoteAdmin(admin.ModelAdmin):
    list_display = ('petition', 'user', 'created_at')
    search_fields = ('petition__title', 'user__username')
