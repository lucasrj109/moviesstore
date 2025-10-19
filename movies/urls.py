from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='movies.index'),
    path('<int:id>/', views.show, name='movies.show'),
    path('<int:id>/review/create/', views.create_review, name='movies.create_review'),
    path('<int:id>/review/<int:review_id>/edit/', views.edit_review, name='movies.edit_review'),
    path('<int:id>/review/<int:review_id>/delete/', views.delete_review, name='movies.delete_review'),
    path('checkout-review/', views.leave_checkout_review, name='leave_checkout_review'),
    path('checkout-review/thankyou/', views.checkout_review_thankyou, name='checkout_review_thankyou'),
    path('reviews/', views.view_checkout_reviews, name='view_checkout_reviews'),
    path('<int:id>/rate/', views.rate_movie, name='movies.rate'),
    path('trending/', views.trending_map, name='movies.trending'),
    path('trending/data', views.trending_data, name='movies.trending_data'),
]