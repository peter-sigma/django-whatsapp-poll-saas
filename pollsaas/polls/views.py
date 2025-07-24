from django.shortcuts import render

# Create your views here.
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import Poll, Choice, Vote

# Placeholder views for Day 5
# These will be fully implemented in upcoming days

def poll_list(request):
    """List all polls (placeholder)"""
    return HttpResponse("Poll list view - Coming soon in Day 8-10!")

@login_required
def poll_create(request):
    """Create a new poll (placeholder)"""
    return HttpResponse("Poll creation view - Coming soon in Day 8-10!")

def poll_detail(request, slug):
    """Poll detail view (placeholder)"""
    poll = get_object_or_404(Poll, slug=slug)
    return HttpResponse(f"Poll detail for: {poll.title} - Coming soon in Day 8-10!")

@login_required
def poll_edit(request, slug):
    """Edit poll (placeholder)"""
    poll = get_object_or_404(Poll, slug=slug)
    return HttpResponse(f"Edit poll: {poll.title} - Coming soon!")

@login_required
def poll_delete(request, slug):
    """Delete poll (placeholder)"""
    poll = get_object_or_404(Poll, slug=slug)
    return HttpResponse(f"Delete poll: {poll.title} - Coming soon!")

def vote(request, slug):
    """Public voting view (placeholder)"""
    poll = get_object_or_404(Poll, slug=slug)
    return HttpResponse(f"Voting for: {poll.title} - Coming soon in Day 11-12!")

def results(request, slug):
    """Poll results view (placeholder)"""
    poll = get_object_or_404(Poll, slug=slug)
    return HttpResponse(f"Results for: {poll.title} - Coming soon in Day 13-14!")

# API endpoints (placeholders for Day 15-16)
def poll_results_api(request, slug):
    """API endpoint for real-time results"""
    poll = get_object_or_404(Poll, slug=slug)
    return JsonResponse({
        'status': 'placeholder',
        'message': 'Real-time API coming in Day 15-16!'
    })

@require_http_methods(["POST"])
def vote_api(request, slug):
    """API endpoint for voting"""
    poll = get_object_or_404(Poll, slug=slug)
    return JsonResponse({
        'status': 'placeholder',
        'message': 'Voting API coming in Day 15-16!'
    })

# Premium features (placeholders for Day 25-28)
@login_required
def poll_analytics(request, slug):
    """Poll analytics view (premium feature)"""
    poll = get_object_or_404(Poll, slug=slug)
    return HttpResponse(f"Analytics for: {poll.title} - Coming in Day 25-28!")

@login_required
def poll_export(request, slug):
    """Export poll data (premium feature)"""
    poll = get_object_or_404(Poll, slug=slug)
    return HttpResponse(f"Export data for: {poll.title} - Coming in Day 25-28!")