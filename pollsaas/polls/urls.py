from django.urls import path
from . import views

app_name = 'polls'

urlpatterns = [
    # Poll management URLs
    path('', views.poll_list, name='poll_list'),
    path('create/', views.poll_create, name='poll_create'),
    path('poll/<slug:slug>/', views.poll_detail, name='poll_detail'),
    path('poll/<slug:slug>/edit/', views.poll_edit, name='poll_edit'),
    path('poll/<slug:slug>/delete/', views.poll_delete, name='poll_delete'),
    
    # Public voting URLs
    path('vote/<slug:slug>/', views.vote, name='vote'),
    path('results/<slug:slug>/', views.results, name='results'),
    
    # AJAX endpoints for real-time updates (Day 15-16)
    path('api/poll/<slug:slug>/results/', views.poll_results_api, name='poll_results_api'),
    path('api/poll/<slug:slug>/vote/', views.vote_api, name='vote_api'),
    
    # Admin/management URLs
    path('poll/<slug:slug>/analytics/', views.poll_analytics, name='poll_analytics'),
    path('poll/<slug:slug>/export/', views.poll_export, name='poll_export'),
]