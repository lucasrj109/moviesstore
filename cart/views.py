from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from movies.models import Movie
from .utils import calculate_cart_total
from .models import Order, Item
from django.conf import settings
from django.views.decorators.http import require_POST 
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import login_required
def index(request):
    cart_total = 0
    movies_in_cart = []
    cart = request.session.get('cart', {})
    movie_ids = list(cart.keys())
    if (movie_ids != []):
        movies_in_cart = Movie.objects.filter(id__in=movie_ids)
        cart_total = calculate_cart_total(cart, movies_in_cart)
    template_data = {}
    template_data['title'] = 'Cart'
    template_data['movies_in_cart'] = movies_in_cart
    template_data['cart_total'] = cart_total
    return render(request, 'cart/index.html', {
        'template_data': template_data,
        'GEOCODING_API_KEY': settings.GEOCODING_API_KEY,
    })
def add(request, id):
    get_object_or_404(Movie, id=id)
    cart = request.session.get('cart', {})
    cart[id] = request.POST['quantity']
    request.session['cart'] = cart
    return redirect('cart.index')
def clear(request):
    request.session['cart'] = {}
    return redirect('cart.index')
@login_required
def purchase(request):
    cart = request.session.get('cart', {})
    movie_ids = list(cart.keys())
    if (movie_ids == []):
        return redirect('cart.index')
    movies_in_cart = Movie.objects.filter(id__in=movie_ids)
    cart_total = calculate_cart_total(cart, movies_in_cart)
    order = Order()
    order.user = request.user
    order.total = cart_total
    order.save()

    geo = request.session.get('geo') or {}
    order.latitude   = geo.get('lat')
    order.longitude  = geo.get('lng')
    order.city       = geo.get('city')
    order.state      = geo.get('state')
    order.country    = geo.get('country')
    order.postal     = geo.get('postal')
    order.region_key = geo.get('region_key')
    order.save()
    request.session.pop('geo', None)

    for movie in movies_in_cart:
        item = Item()
        item.movie = movie
        item.price = movie.price
        item.order = order
        item.quantity = cart[str(movie.id)]
        item.save()
    request.session['cart'] = {}
    template_data = {}
    template_data['title'] = 'Purchase confirmation'
    template_data['order_id'] = order.id
    return render(request, 'cart/purchase.html',
        {'template_data': template_data})
@require_POST
def set_location(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        request.session['geo'] = {
            'lat': payload.get('lat'),
            'lng': payload.get('lng'),
            'city': payload.get('city'),
            'state': payload.get('state'),
            'country': payload.get('country'),
            'postal': payload.get('postal'),
            'region_key': payload.get('region_key'),
        }
        request.session.modified = True
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)