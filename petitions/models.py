from django.conf import settings
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User

#User = settings.AUTH_USER_MODEL

class Petition(models.Model):
    title = models.CharField(max_length=255)
    director = models.CharField(max_length=255)
    year = models.PositiveIntegerField()
    description = models.TextField()
    image = models.ImageField(upload_to="petition_images/", blank=True, null=True)
    posted_by = models.ForeignKey(User, related_name="petitions", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # newest first

    def __str__(self):
        return f"{self.title} ({self.year})"

    def get_absolute_url(self):
        return reverse('petitions:detail', args=[self.pk])

    @property
    def votes_count(self):
        # quick convenience property
        return self.votes.count()

class PetitionVote(models.Model):
    petition = models.ForeignKey(Petition, related_name="votes", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="petition_votes", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('petition', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} -> {self.petition}"
