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

def trending_map(request):
    return render(request, 'movies/trending.html', {
        'MAPS_API_KEY': settings.MAPS_API_KEY
    })

def trending_data(request):
    """
    Returns JSON data of trending movies by region for the Google Map.
    Each region includes coordinates, total purchases, and top 3 movies 
    (with id, name, count, and image URL).
    """
    try:
        # ---- 1. Parse and validate time window ----
        window = request.GET.get('window', '30d')
        try:
            days = int(window[:-1]) if window.endswith('d') else int(window)
        except Exception:
            days = 30
        days = max(days, 1)
        since = timezone.now() - timedelta(days=days)

        # ---- 2. Query Item objects (sales data) ----
        # We only include orders with valid region + coordinates
        qs = (
            Item.objects
            .filter(
                order__date__gte=since,
                order__region_key__isnull=False,
                order__latitude__isnull=False,
                order__longitude__isnull=False,
            )
            .values(
                'order__region_key',
                'order__state',
                'order__country',
                'order__latitude',
                'order__longitude',
                'movie__id',
                'movie__name',
                'movie__image',   # include movie image field
                'quantity',
            )
        )

        # ---- 3. Group purchases by region ----
        regions = {}
        for row in qs:
            rk = row['order__region_key']
            region = regions.setdefault(rk, {
                'region_key': rk,
                'state': row['order__state'],
                'country': row['order__country'],
                '_lat_sum': 0.0, '_lng_sum': 0.0, '_n': 0,
                'total_purchases': 0,
                'movie_counts': {}  # movie_id -> {name, image, count}
            })

            # Add lat/lng for averaging region center
            region['_lat_sum'] += float(row['order__latitude'])
            region['_lng_sum'] += float(row['order__longitude'])
            region['_n'] += 1

            # Track movie sales count
            qty = int(row.get('quantity') or 0)
            region['total_purchases'] += qty
            mid = row['movie__id']
            mname = row['movie__name']
            mimage_rel = row.get('movie__image')
            mimage = None
            if mimage_rel:
                # Combine MEDIA_URL with relative path to get full URL
                mimage = settings.MEDIA_URL.rstrip('/') + '/' + mimage_rel.lstrip('/')

            movie_info = region['movie_counts'].setdefault(
                mid, {'name': mname, 'image': mimage, 'count': 0}
            )

            movie_info['count'] += qty

        # ---- 4. Build response payload ----
        payload = []
        for region in regions.values():
            n = max(region['_n'], 1)

            # Sort top movies by sales count, limit to top 3
            top_movies = sorted(
                [
                    {
                        'id': mid,
                        'name': info['name'],
                        'image': info['image'],
                        'count': info['count']
                    }
                    for mid, info in region['movie_counts'].items()
                ],
                key=lambda x: (-x['count'], x['name'])
            )[:3]

            payload.append({
                'region_key': region['region_key'],
                'state': region['state'],
                'country': region['country'],
                'lat': round(region['_lat_sum'] / n, 6),
                'lng': round(region['_lng_sum'] / n, 6),
                'total_purchases': region['total_purchases'],
                'top': top_movies,
            })

        # Sort regions by total purchases descending
        payload.sort(key=lambda r: (-r['total_purchases'], r['region_key']))

        return JsonResponse({'regions': payload})

    except Exception as e:
        # Log error (optional: print or use logging)
        print("Error in trending_data:", e)
        return JsonResponse({'regions': []})

