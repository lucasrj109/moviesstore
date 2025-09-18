from django.db import models
from django.contrib.auth.models import User
class Movie(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    price = models.IntegerField()
    description = models.TextField()
    image = models.ImageField(upload_to='movie_images/')
    def __str__(self):
        return str(self.id) + ' - ' + self.name
class Review(models.Model):
    id = models.AutoField(primary_key=True)
    comment = models.CharField(max_length=255)
    date = models.DateTimeField(auto_now_add=True)
    movie = models.ForeignKey(Movie,
        on_delete=models.CASCADE)
    user = models.ForeignKey(User,
        on_delete=models.CASCADE)
    def __str__(self):
        return str(self.id) + ' - ' + self.movie.name

class CheckoutExperienceReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, blank=True)
    is_anonymous = models.BooleanField(default=False)
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def display_name(self):
        if self.is_anonymous or not self.name:
            return "Anonymous"
        return self.name

    def __str__(self):
        return f"Review by {self.display_name()} on {self.created_at.strftime('%Y-%m-%d')}"