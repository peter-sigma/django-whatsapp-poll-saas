from django.shortcuts import render, redirect

# Create your views here.
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse

from .models import Poll, Choice, Vote
from .forms import PollCreateForm, PollEditForm, QuickPollForm



class PollCreateView(LoginRequiredMixin, CreateView):
    """
    Class-based view for creating polls with full features
    """
    model = Poll
    form_class = PollCreateForm
    template_name = 'polls/create_poll.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(
            self.request, 
            f'🎉 Poll "{form.instance.title}" created successfully! Share it with your WhatsApp group.'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            'There were some errors with your poll. Please check the form below.'
        )
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('polls:poll_detail', kwargs={'slug': self.object.slug})



@login_required
def create_poll_view(request):
    """
    Function-based view for poll creation with step-by-step process
    """
    if request.method == 'POST':
        form = PollCreateForm(request.POST, user=request.user)
        if form.is_valid():
            poll = form.save()
            messages.success(
                request, 
                f'🎉 Poll "{poll.title}" created successfully!'
            )
            return redirect('polls:poll_success', slug=poll.slug)
        else:
            messages.error(
                request,
                'Please fix the errors below and try again.'
            )
    else:
        form = PollCreateForm(user=request.user)
    
    # Get user's existing polls count for context
    user_polls_count = Poll.objects.filter(creator=request.user).count()
    max_polls = 50 if request.user.is_premium else 1
    remaining_polls = max_polls - user_polls_count
    
    context = {
        'form': form,
        'user_polls_count': user_polls_count,
        'max_polls': max_polls,
        'is_premium': request.user.is_premium,
        'remaining_polls': remaining_polls
    }
    
    return render(request, 'polls/create_poll.html', context)


@login_required
def quick_poll_view(request):
    """
    Quick poll creation for simple polls
    """
    if request.method == 'POST':
        form = QuickPollForm(request.POST)
        if form.is_valid():
            poll = form.create_poll(request.user)
            messages.success(
                request,
                f'✨ Quick poll "{poll.title}" created! Ready to share.'
            )
            return redirect('polls:poll_success', slug=poll.slug)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = QuickPollForm()
    
    context = {
        'form': form,
        'is_quick_poll': True,
    }
    
    return render(request, 'polls/quick_poll.html', context)


def poll_success_view(request, slug):
    """
    Success page after poll creation with sharing options
    """
    poll = get_object_or_404(Poll, slug=slug)
    
    # Check if user is the creator or poll is public
    if poll.creator != request.user and not poll.allow_anonymous:
        messages.error(request, 'Poll not found.')
        return redirect('polls:dashboard')
    
    context = {
        'poll': poll,
        'vote_url': request.build_absolute_uri(poll.get_vote_url()),
        'whatsapp_url': poll.get_whatsapp_share_url(),
        'show_sharing': True,
    }
    
    return render(request, 'polls/poll_success.html', context)


@login_required
def poll_preview_view(request, slug):
    """
    Preview poll before publishing (for drafts)
    """
    poll = get_object_or_404(Poll, slug=slug, creator=request.user)
    
    context = {
        'poll': poll,
        'is_preview': True,
        'choices': poll.choices.all(),
    }
    
    return render(request, 'polls/poll_preview.html', context)


@login_required
@require_http_methods(["POST"])
def publish_poll_view(request, slug):
    """
    Publish a draft poll
    """
    poll = get_object_or_404(Poll, slug=slug, creator=request.user)
    
    if poll.status != 'draft':
        messages.error(request, 'Poll is already published.')
        return redirect('polls:poll_detail', slug=slug)
    
    # Validate poll has choices
    if poll.choices.count() < 2:
        messages.error(request, 'Poll must have at least 2 choices before publishing.')
        return redirect('polls:poll_preview', slug=slug)
    
    poll.status = 'active'
    poll.is_active = True
    poll.save()
    
    messages.success(request, f'✅ Poll "{poll.title}" is now live!')
    return redirect('polls:poll_success', slug=slug)


class PollEditView(LoginRequiredMixin, UpdateView):
    """
    Edit existing poll (limited editing after votes)
    """
    model = Poll
    form_class = PollEditForm
    template_name = 'polls/edit_poll.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        # Only allow editing own polls
        return Poll.objects.filter(creator=self.request.user)
    
    def form_valid(self, form):
        messages.success(
            self.request,
            f'✅ Poll "{form.instance.title}" updated successfully!'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('polls:poll_detail', kwargs={'slug': self.object.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_votes'] = self.object.total_votes > 0
        context['choices'] = self.object.choices.all()
        return context
    


@login_required
def poll_detail_view(request, slug):
    """
    Detailed view of poll for creators
    """
    poll = get_object_or_404(Poll, slug=slug)
    
    # Check permissions
    if poll.creator != request.user and not poll.allow_anonymous:
        messages.error(request, 'Poll not found.')
        return redirect('polls:dashboard')
    
    choices = poll.choices.all()
    recent_votes = poll.votes.select_related('choice', 'voter').order_by('-voted_at')[:10]
    
    context = {
        'poll': poll,
        'choices': choices,
        'recent_votes': recent_votes,
        'vote_url': request.build_absolute_uri(poll.get_vote_url()),
        'whatsapp_url': poll.get_whatsapp_share_url(),
        'is_creator': poll.creator == request.user,
    }
    
    return render(request, 'polls/poll_detail.html', context)


@login_required
@require_http_methods(["POST"])
def delete_poll_view(request, slug):
    """
    Delete a poll (with confirmation)
    """
    poll = get_object_or_404(Poll, slug=slug, creator=request.user)
    
    poll_title = poll.title
    poll.delete()
    
    # Update user's poll count
    request.user.polls_created = max(0, request.user.polls_created - 1)
    request.user.save(update_fields=['polls_created'])
    
    messages.success(request, f'🗑️ Poll "{poll_title}" has been deleted.')
    return redirect('polls:dashboard')

@login_required
@require_http_methods(["POST"])
def toggle_poll_status_view(request, slug):
    """
    Toggle poll active/inactive status
    """
    poll = get_object_or_404(Poll, slug=slug, creator=request.user)
    
    poll.is_active = not poll.is_active
    poll.save(update_fields=['is_active'])
    
    status = "activated" if poll.is_active else "deactivated"
    messages.success(request, f'✅ Poll "{poll.title}" has been {status}.')
    
    return redirect('polls:poll_detail', slug=slug)


@require_http_methods(["GET"])
def poll_stats_api(request, slug):
    """
    API endpoint for real-time poll statistics
    """
    poll = get_object_or_404(Poll, slug=slug)
    
    # Check if user can view results
    if not poll.show_results and poll.creator != request.user:
        return JsonResponse({'error': 'Results not available'}, status=403)
    
    choices_data = []
    for choice in poll.choices.all():
        choices_data.append({
            'id': choice.id,
            'text': choice.text,
            'votes': choice.votes,
            'percentage': choice.vote_percentage,
        })
    
    data = {
        'poll_id': poll.id,
        'title': poll.title,
        'total_votes': poll.total_votes,
        'unique_voters': poll.unique_voters,
        'choices': choices_data,
        'is_active': poll.is_active,
        'can_vote': poll.can_vote,
        'expires_at': poll.expires_at.isoformat() if poll.expires_at else None,
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)


def poll_share_stats(request, slug):
    """
    Public stats for sharing (limited data)
    """
    poll = get_object_or_404(Poll, slug=slug)
    
    if not poll.show_results:
        return JsonResponse({'error': 'Results not public'}, status=403)
    
    data = {
        'title': poll.title,
        'total_votes': poll.total_votes,
        'choices_count': poll.choices.count(),
        'is_active': poll.can_vote,
        'created_at': poll.created_at.date().isoformat(),
    }
    
    return JsonResponse(data)


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