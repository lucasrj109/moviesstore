from django.urls import path
from . import views

app_name = 'petitions'

urlpatterns = [
    path('', views.petition_list, name='index'),
    path('create/', views.petition_create, name='create'),
    path('<int:pk>/', views.petition_detail, name='detail'),
    path('<int:pk>/vote/', views.petition_vote, name='vote'),  # POST only
]
