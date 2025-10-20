from django.shortcuts import render, redirect, get_object_or_404
from .forms import CheckoutExperienceReviewForm
from .models import Movie, Review, CheckoutExperienceReview, Rating
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
from django.http import JsonResponse
from datetime import timedelta
from cart.models import Order, Item
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
    movie = get_object_or_404(Movie, id=id)
    reviews = Review.objects.filter(movie=movie)
    ratings = Rating.objects.filter(movie=movie)

    avg_rating = ratings.aggregate(avg=models.Avg('score'))['avg']
    avg_rating = round(avg_rating or 0, 1)

    user_rating = None
    if request.user.is_authenticated:
        user_rating_obj = ratings.filter(user=request.user).first()
        user_rating = user_rating_obj.score if user_rating_obj else None

    template_data = {
        'title': movie.name,
        'movie': movie,
        'reviews': reviews,
        'avg_rating': f"{avg_rating:.1f}",
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

    if not (1 <= score <= 5):
        return JsonResponse({'error': 'Score must be between 1 and 5'}, status=400)

    rating, _ = Rating.objects.update_or_create(
        user=request.user,
        movie=movie,
        defaults={'score': score}
    )

    avg_rating = (
        Rating.objects.filter(movie=movie)
        .aggregate(avg=models.Avg('score'))['avg']
    )
    avg_rating = round(avg_rating or 0, 1)

    return JsonResponse({
        'message': 'Rating saved successfully',
        'average_rating': f"{avg_rating:.1f}",
        'your_rating': rating.score,
    })

def trending_map(request):
    return render(request, 'movies/trending.html', {
        'MAPS_API_KEY': settings.MAPS_API_KEY
    })

def trending_data(request):
    try:
        window = request.GET.get('window', '30d')
        # parse "7d", "30d", "90d" or raw int days
        try:
            days = int(window[:-1]) if window.endswith('d') else int(window)
        except Exception:
            days = 30
        days = max(days, 1)
        since = timezone.now() - timedelta(days=days)

        # Pull purchases joined to Order's stamped location
        qs = (Item.objects
              .filter(order__date__gte=since,
                      order__region_key__isnull=False,
                      order__latitude__isnull=False,
                      order__longitude__isnull=False)
              .values('order__region_key', 'order__state', 'order__country',
                      'order__latitude', 'order__longitude',
                      'movie__name', 'quantity'))

        regions = {}
        for row in qs:
            rk = row['order__region_key']
            b = regions.setdefault(rk, {
                'region_key': rk,
                'state': row['order__state'],
                'country': row['order__country'],
                '_lat_sum': 0.0, '_lng_sum': 0.0, '_n': 0,
                'total_purchases': 0,
                'movie_counts': {}
            })
            b['_lat_sum'] += float(row['order__latitude'])
            b['_lng_sum'] += float(row['order__longitude'])
            b['_n'] += 1

            qty = int(row.get('quantity') or 0)
            b['total_purchases'] += qty
            name = row['movie__name']
            b['movie_counts'][name] = b['movie_counts'].get(name, 0) + qty

        payload = []
        for rk, b in regions.items():
            n = max(b['_n'], 1)
            top = sorted(
                [{'movie': m, 'count': c} for m, c in b['movie_counts'].items()],
                key=lambda x: (-x['count'], x['movie'])
            )[:3]
            payload.append({
                'region_key': rk,
                'state': b['state'],
                'country': b['country'],
                'lat': round(b['_lat_sum'] / n, 6),
                'lng': round(b['_lng_sum'] / n, 6),
                'total_purchases': b['total_purchases'],
                'top': top
            })

        payload.sort(key=lambda r: (-r['total_purchases'], r['region_key']))
        return JsonResponse({'regions': payload})
    except Exception as e:
        return JsonResponse({'regions': []})