from django.shortcuts import render, redirect, get_object_or_404
from .forms import CheckoutExperienceReviewForm
from .models import Movie, Review, CheckoutExperienceReview, Rating
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import models
import json

def index(request):
    search_term = request.GET.get('search')
    if search_term:
        movies = Movie.objects.filter(name__icontains=search_term)
    else:
        movies = Movie.objects.all()
    template_data = {}
    template_data['title'] = 'Movies'
    template_data['movies'] = movies
    return render(request, 'movies/index.html',
                  {'template_data': template_data})

def show(request, id):
    movie = Movie.objects.get(id=id)
    reviews = Review.objects.filter(movie=movie)
    ratings = Rating.objects.filter(movie=movie)
    avg_rating = round(ratings.aggregate(models.Avg('score'))['score__avg'] or 0, 1)

    user_rating = None
    if request.user.is_authenticated:
        user_rating_obj = Rating.objects.filter(movie=movie, user=request.user).first()
        if user_rating_obj:
            user_rating = user_rating_obj.score

    template_data = {
        'title': movie.name,
        'movie': movie,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'user_rating': user_rating,
    }
    return render(request, 'movies/show.html', {'template_data': template_data})
@login_required
def create_review(request, id):
    if request.method == 'POST' and request.POST['comment']!= '':
        movie = Movie.objects.get(id=id)
        review = Review()
        review.comment = request.POST['comment']
        review.movie = movie
        review.user = request.user
        review.save()
        return redirect('movies.show', id=id)
    else:
        return redirect('movies.show', id=id)
@login_required
def edit_review(request, id, review_id):
    review = get_object_or_404(Review, id=review_id)
    if request.user != review.user:
        return redirect('movies.show', id=id)
    if request.method == 'GET':
        template_data = {}
        template_data['title'] = 'Edit Review'
        template_data['review'] = review
        return render(request, 'movies/edit_review.html',
            {'template_data': template_data})
    elif request.method == 'POST' and request.POST['comment'] != '':
        review = Review.objects.get(id=review_id)
        review.comment = request.POST['comment']
        review.save()
        return redirect('movies.show', id=id)
    else:
        return redirect('movies.show', id=id)
@login_required
def delete_review(request, id, review_id):
    review = get_object_or_404(Review, id=review_id,
        user=request.user)
    review.delete()
    return redirect('movies.show', id=id)

@login_required
def leave_checkout_review(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        review_text = request.POST.get('review_text')

        CheckoutExperienceReview.objects.create(
            name=name if name else None,
            review_text=review_text
        )
        return redirect('checkout_review_thankyou')

    return render(request, 'movies/leave_checkout_review.html')

def view_checkout_reviews(request):
    reviews = CheckoutExperienceReview.objects.order_by('-created_at')
    return render(request, 'movies/view_checkout_reviews.html', {'reviews': reviews})


def checkout_review_thankyou(request):
    return render(request, 'movies/checkout_review_thankyou.html')

@login_required
@require_POST
def rate_movie(request, id):
    movie = get_object_or_404(Movie, id=id)
    try:
        data = json.loads(request.body)
        score = int(data.get('score'))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    if score < 1 or score > 5:
        return JsonResponse({'error': 'Score must be between 1 and 5'}, status=400)

    rating, created = Rating.objects.update_or_create(
        user=request.user, movie=movie, defaults={'score': score}
    )

    # Calculate updated average rating
    all_ratings = Rating.objects.filter(movie=movie)
    avg = round(all_ratings.aggregate(models.Avg('score'))['score__avg'] or 0, 1)

    return JsonResponse({
        'message': 'Rating saved successfully',
        'average_rating': avg,
        'your_rating': rating.score,
    })
