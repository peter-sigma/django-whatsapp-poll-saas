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
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt

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


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Extract user agent from request"""
    return request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length


def vote_view(request, slug):
    """
    Public voting interface - the main voting page
    """
    poll = get_object_or_404(Poll, slug=slug)
    
    # Check if poll allows voting
    if not poll.can_vote:
        context = {
            'poll': poll,
            'error_message': 'This poll is no longer accepting votes.',
            'is_expired': poll.is_expired,
            'is_closed': not poll.is_active
        }
        return render(request, 'polls/vote_closed.html', context)
    
    # Check if login is required
    if poll.require_login and not request.user.is_authenticated:
        messages.info(request, 'You need to log in to vote on this poll.')
        return redirect('accounts:login')
    
    # Get client info for duplicate checking
    client_ip = get_client_ip(request)
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    
    # Check if user has already voted
    has_voted = False
    previous_votes = []
    
    if request.user.is_authenticated:
        # Check by user
        previous_votes = Vote.objects.filter(poll=poll, voter=request.user)
        has_voted = previous_votes.exists()
    else:
        # Check by IP and session for anonymous users
        previous_votes = Vote.objects.filter(
            poll=poll, 
            voter_ip=client_ip,
            voter_session=session_key
        )
        has_voted = previous_votes.exists()
    
    # If already voted and multiple votes not allowed, show results or thank you
    if has_voted and not poll.allow_multiple_votes:
        # Get the choices they voted for
        voted_choices = [vote.choice for vote in previous_votes]
        
        if poll.show_results:
            return redirect('polls:results', slug=slug)
        else:
            context = {
                'poll': poll,
                'voted_choices': voted_choices,
                'already_voted': True
            }
            return render(request, 'polls/already_voted.html', context)
    
    # Handle POST request (voting)
    if request.method == 'POST':
        return handle_vote_submission(request, poll, client_ip, session_key)
    
    # GET request - show voting form
    choices = poll.choices.filter(is_active=True).order_by('order')
    
    context = {
        'poll': poll,
        'choices': choices,
        'can_vote_multiple': poll.allow_multiple_votes,
        'show_results_after': poll.show_results,
        'is_anonymous': not request.user.is_authenticated,
        'has_voted': has_voted,
        'previous_votes': [vote.choice.id for vote in previous_votes] if has_voted else []
    }
    
    return render(request, 'polls/vote.html', context)


@transaction.atomic
def handle_vote_submission(request, poll, client_ip, session_key):
    """
    Handle the actual vote submission with validation and processing
    """
    try:
        # Get selected choices from form
        if poll.poll_type == 'multiple' and poll.allow_multiple_votes:
            # Multiple choice poll
            choice_ids = request.POST.getlist('choices')
        else:
            # Single choice poll
            choice_id = request.POST.get('choice')
            choice_ids = [choice_id] if choice_id else []
        
        if not choice_ids:
            messages.error(request, 'Please select at least one option.')
            return redirect('polls:vote', slug=poll.slug)
        
        # Validate choice IDs
        valid_choices = Choice.objects.filter(
            id__in=choice_ids, 
            poll=poll, 
            is_active=True
        )
        
        if len(valid_choices) != len(choice_ids):
            messages.error(request, 'Invalid choice selected.')
            return redirect('polls:vote', slug=poll.slug)
        
        # Check vote limits for poll type
        if poll.poll_type == 'single' and len(choice_ids) > 1:
            messages.error(request, 'You can only select one option for this poll.')
            return redirect('polls:vote', slug=poll.slug)
        
        if poll.poll_type == 'yes_no' and len(choice_ids) > 1:
            messages.error(request, 'You can only select one option for Yes/No polls.')
            return redirect('polls:vote', slug=poll.slug)
        
        # Check for duplicate voting
        if not poll.allow_multiple_votes:
            existing_votes = None
            if request.user.is_authenticated:
                existing_votes = Vote.objects.filter(poll=poll, voter=request.user)
            else:
                existing_votes = Vote.objects.filter(
                    poll=poll, 
                    voter_ip=client_ip,
                    voter_session=session_key
                )
            
            if existing_votes.exists():
                messages.warning(request, 'You have already voted on this poll.')
                if poll.show_results:
                    return redirect('polls:results', slug=poll.slug)
                else:
                    return redirect('polls:vote', slug=poll.slug)
        
        # Create vote records
        votes_created = []
        user_agent = get_user_agent(request)
        
        for choice in valid_choices:
            vote = Vote.objects.create(
                poll=poll,
                choice=choice,
                voter=request.user if request.user.is_authenticated else None,
                voter_ip=client_ip,
                voter_session=session_key,
                user_agent=user_agent,
                is_valid=True
            )
            votes_created.append(vote)
            
            # Increment choice vote count
            choice.increment_votes()
        
        # Update poll statistics
        poll.increment_vote_count()
        
        # Check if this is a new unique voter
        if request.user.is_authenticated:
            # Check if user has voted on this poll before
            if not Vote.objects.filter(
                poll=poll, 
                voter=request.user
            ).exclude(id__in=[v.id for v in votes_created]).exists():
                poll.increment_voter_count()
        else:
            # Check if this IP/session has voted before
            if not Vote.objects.filter(
                poll=poll,
                voter_ip=client_ip,
                voter_session=session_key
            ).exclude(id__in=[v.id for v in votes_created]).exists():
                poll.increment_voter_count()
        
        # Success message
        choice_names = ', '.join([choice.text for choice in valid_choices])
        messages.success(
            request, 
            f'✅ Thank you! Your vote{"s" if len(valid_choices) > 1 else ""} for "{choice_names}" ha{"ve" if len(valid_choices) > 1 else "s"} been recorded.'
        )
        
        # Redirect based on poll settings
        if poll.show_results:
            return redirect('polls:results', slug=poll.slug)
        else:
            return redirect('polls:vote_success', slug=poll.slug)
            
    except Exception as e:
        # Log the error (in production, use proper logging)
        print(f"Vote submission error: {e}")
        messages.error(request, 'There was an error processing your vote. Please try again.')
        return redirect('polls:vote', slug=poll.slug)


def vote_success_view(request, slug):
    """
    Thank you page after successful voting (when results are hidden)
    """
    poll = get_object_or_404(Poll, slug=slug)
    
    # Get user's votes for this poll
    user_votes = []
    if request.user.is_authenticated:
        user_votes = Vote.objects.filter(poll=poll, voter=request.user).select_related('choice')
    else:
        client_ip = get_client_ip(request)
        session_key = request.session.session_key
        user_votes = Vote.objects.filter(
            poll=poll,
            voter_ip=client_ip,
            voter_session=session_key
        ).select_related('choice')
    
    context = {
        'poll': poll,
        'user_votes': user_votes,
        'voted_choices': [vote.choice for vote in user_votes],
        'can_see_results': poll.show_results,
        'results_url': poll.get_results_url() if poll.show_results else None
    }
    
    return render(request, 'polls/vote_success.html', context)


def results_view(request, slug):
    """
    Display poll results with live updates
    """
    poll = get_object_or_404(Poll, slug=slug)
    
    # Check if results are public or user is creator
    can_view_results = (
        poll.show_results or 
        (request.user.is_authenticated and poll.creator == request.user)
    )
    
    if not can_view_results:
        messages.error(request, 'Results are not available for this poll.')
        return redirect('polls:vote', slug=poll.slug)
    
    # Get choices with vote counts
    choices = poll.choices.filter(is_active=True).order_by('order')
    
    # Prepare data for charts
    chart_data = {
        'labels': [choice.text for choice in choices],
        'data': [choice.votes for choice in choices],
        'backgroundColor': [
            '#25d366', '#128c7e', '#075e54', '#34ce57', '#1fa045',
            '#ffc107', '#fd7e14', '#dc3545', '#6f42c1', '#20c997'
        ][:len(choices)]
    }
    
    # Get recent votes for activity feed
    recent_votes = poll.votes.select_related('choice', 'voter').order_by('-voted_at')[:10]
    
    # Check if current user has voted
    user_has_voted = False
    user_votes = []
    
    if request.user.is_authenticated:
        user_votes = Vote.objects.filter(poll=poll, voter=request.user).select_related('choice')
        user_has_voted = user_votes.exists()
    else:
        client_ip = get_client_ip(request)
        session_key = request.session.session_key
        if session_key:
            user_votes = Vote.objects.filter(
                poll=poll,
                voter_ip=client_ip,
                voter_session=session_key
            ).select_related('choice')
            user_has_voted = user_votes.exists()
    
    context = {
        'poll': poll,
        'choices': choices,
        'chart_data': json.dumps(chart_data),
        'recent_votes': recent_votes,
        'user_has_voted': user_has_voted,
        'user_votes': user_votes,
        'can_vote': poll.can_vote and (not user_has_voted or poll.allow_multiple_votes),
        'vote_url': poll.get_vote_url(),
        'is_creator': request.user.is_authenticated and poll.creator == request.user,
        'whatsapp_url': poll.get_whatsapp_share_url(),
    }
    
    return render(request, 'polls/results.html', context)


@require_http_methods(["GET"])
def poll_results_api(request, slug):
    """
    API endpoint for real-time poll results (HTMX/AJAX)
    """
    poll = get_object_or_404(Poll, slug=slug)
    
    # Check permissions
    can_view_results = (
        poll.show_results or 
        (request.user.is_authenticated and poll.creator == request.user)
    )
    
    if not can_view_results:
        return JsonResponse({'error': 'Results not available'}, status=403)
    
    # Get updated choice data
    choices_data = []
    for choice in poll.choices.filter(is_active=True).order_by('order'):
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


@csrf_exempt
@require_http_methods(["POST"])
def vote_api(request, slug):
    """
    API endpoint for voting (for HTMX/AJAX submissions)
    """
    poll = get_object_or_404(Poll, slug=slug)
    
    if not poll.can_vote:
        return JsonResponse({
            'success': False,
            'error': 'This poll is no longer accepting votes.'
        }, status=400)
    
    # Check if login is required
    if poll.require_login and not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Login required to vote on this poll.',
            'redirect': reverse('accounts:login')
        }, status=401)
    
    try:
        # Parse JSON data if available, otherwise use POST data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            choice_ids = data.get('choices', [])
        else:
            if poll.allow_multiple_votes:
                choice_ids = request.POST.getlist('choices')
            else:
                choice_id = request.POST.get('choice')
                choice_ids = [choice_id] if choice_id else []
        
        if not choice_ids:
            return JsonResponse({
                'success': False,
                'error': 'Please select at least one option.'
            }, status=400)
        
        # Get client info
        client_ip = get_client_ip(request)
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        # Process the vote using the same logic as regular form submission
        with transaction.atomic():
            # Validate choices exist and belong to this poll
            valid_choices = Choice.objects.filter(
                id__in=choice_ids,
                poll=poll,
                is_active=True
            )
            
            if len(valid_choices) != len(choice_ids):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid choice selected.'
                }, status=400)
            
            # Check for duplicate voting
            if not poll.allow_multiple_votes:
                existing_votes = None
                if request.user.is_authenticated:
                    existing_votes = Vote.objects.filter(poll=poll, voter=request.user)
                else:
                    existing_votes = Vote.objects.filter(
                        poll=poll,
                        voter_ip=client_ip,
                        voter_session=session_key
                    )
                
                if existing_votes.exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'You have already voted on this poll.',
                        'redirect': reverse('polls:results', kwargs={'slug': slug}) if poll.show_results else None
                    }, status=400)
            
            # Create votes
            votes_created = []
            user_agent = get_user_agent(request)
            
            for choice in valid_choices:
                vote = Vote.objects.create(
                    poll=poll,
                    choice=choice,
                    voter=request.user if request.user.is_authenticated else None,
                    voter_ip=client_ip,
                    voter_session=session_key,
                    user_agent=user_agent,
                    is_valid=True
                )
                votes_created.append(vote)
                choice.increment_votes()
            
            # Update poll stats
            poll.increment_vote_count()
            
            # Update unique voter count if needed
            if request.user.is_authenticated:
                if not Vote.objects.filter(
                    poll=poll,
                    voter=request.user
                ).exclude(id__in=[v.id for v in votes_created]).exists():
                    poll.increment_voter_count()
            else:
                if not Vote.objects.filter(
                    poll=poll,
                    voter_ip=client_ip,
                    voter_session=session_key
                ).exclude(id__in=[v.id for v in votes_created]).exists():
                    poll.increment_voter_count()
        
        # Return success response
        choice_names = [choice.text for choice in valid_choices]
        response_data = {
            'success': True,
            'message': f'Vote recorded for: {", ".join(choice_names)}',
            'voted_choices': [choice.id for choice in valid_choices],
            'redirect': reverse('polls:results', kwargs={'slug': slug}) if poll.show_results else reverse('polls:vote_success', kwargs={'slug': slug})
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data.'
        }, status=400)
    except Exception as e:
        print(f"API vote error: {e}")  # Log in production
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your vote.'
        }, status=500)


# Keep all the existing views from your original file
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


# Add the remaining views from your original file...
@login_required
@require_http_methods(["POST"])
def delete_poll_view(request, slug):
    """Delete a poll (with confirmation)"""
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
    """Toggle poll active/inactive status"""
    poll = get_object_or_404(Poll, slug=slug, creator=request.user)
    
    poll.is_active = not poll.is_active
    poll.save(update_fields=['is_active'])
    
    status = "activated" if poll.is_active else "deactivated"
    messages.success(request, f'✅ Poll "{poll.title}" has been {status}.')
    
    return redirect('polls:poll_detail', slug=slug)


@require_http_methods(["GET"])
def poll_stats_api(request, slug):
    """API endpoint for poll statistics"""
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


# Keep existing placeholder views for other features
def poll_edit(request, slug):
    """Edit poll (placeholder)"""
    poll = get_object_or_404(Poll, slug=slug)
    return HttpResponse(f"Edit poll: {poll.title} - Coming soon!")


def poll_delete(request, slug):
    """Delete poll (placeholder)"""
    poll = get_object_or_404(Poll, slug=slug)
    return HttpResponse(f"Delete poll: {poll.title} - Coming soon!")


def poll_share_stats(request, slug):
    """Public stats for sharing (limited data)"""
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


