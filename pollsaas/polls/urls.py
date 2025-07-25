from django.urls import path
from . import views

app_name = 'polls'

urlpatterns = [
    
    # Public voting URLs
    path('vote/<slug:slug>/', views.vote, name='vote'),
    path('results/<slug:slug>/', views.results, name='results'),
    
    # AJAX endpoints for real-time updates (Day 15-16)
    path('api/poll/<slug:slug>/results/', views.poll_results_api, name='poll_results_api'),
    path('api/poll/<slug:slug>/vote/', views.vote_api, name='vote_api'),
    
    # Admin/management URLs
    path('poll/<slug:slug>/analytics/', views.poll_analytics, name='poll_analytics'),
    path('poll/<slug:slug>/export/', views.poll_export, name='poll_export'),


    path('quick/', views.quick_poll_view, name='quick_poll'),
    path('create-class/', views.PollCreateView.as_view(), name='create_poll_class'),
    
    # Poll management
    path('poll/<slug:slug>/', views.poll_detail_view, name='poll_detail'),
    path('poll/<slug:slug>/edit/', views.PollEditView.as_view(), name='edit_poll'),
    path('poll/<slug:slug>/preview/', views.poll_preview_view, name='poll_preview'),
    path('poll/<slug:slug>/publish/', views.publish_poll_view, name='publish_poll'),
    path('poll/<slug:slug>/delete/', views.delete_poll_view, name='delete_poll'),
    path('poll/<slug:slug>/toggle/', views.toggle_poll_status_view, name='toggle_poll'),
    path('poll/<slug:slug>/success/', views.poll_success_view, name='poll_success'),
    
    # API endpoints
    path('api/poll/<slug:slug>/stats/', views.poll_stats_api, name='poll_stats_api'),
    path('api/poll/<slug:slug>/share-stats/', views.poll_share_stats, name='poll_share_stats'),
    
]