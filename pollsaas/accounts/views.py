from django.shortcuts import render

# Create your views here.
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView
from .forms import CustomUserCreationForm, CustomAuthenticationForm, ContactForm
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone

from polls.models import Poll

User = get_user_model()

class CustomSignUpView(CreateView):
    """
    User registration view
    """
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        """Save the user and log them in"""
        response = super().form_valid(form)
        messages.success(
            self.request, 
            'Account created successfully! You can now log in.'
        )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Sign Up - PollSaaS'
        return context

class CustomLoginView(LoginView):
    """
    User login view
    """
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        """Add success message on login"""
        messages.success(self.request, f'Welcome back, {form.get_user().username}!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Add error message on invalid login"""
        messages.error(self.request, 'Invalid email or password.')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login - PollSaaS'
        return context

class CustomLogoutView(LogoutView):
    """
    User logout view
    """
    next_page = '/'
    

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)

@login_required
def profile_view(request):
    """
    User profile view
    """
    user = request.user
    polls_qs = Poll.objects.filter(creator=user)

    polls_created = polls_qs.count()
    total_votes = polls_qs.aggregate(total=Sum('total_votes'))['total'] or 0

    # Free plan limit (fallback to 1 if not set)
    free_limit = getattr(settings, 'FREE_POLL_LIMIT', 1)

    if getattr(user, 'is_premium_active', False):
        polls_remaining = None   # template will show "Unlimited"
    else:
        polls_remaining = max(0, free_limit - polls_created)
    context = {
        'title': 'Profile - PollSaaS',
        'user': user,
        'polls_created': polls_created,
        'total_votes': total_votes,
        'polls_remaining': user.polls_remaining,
        'is_premium': getattr(user, 'is_premium_active', False),
        'premium_until': getattr(user, 'premium_until', None),
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def dashboard_view(request):
    """
    User dashboard view
    """
   
    user = request.user
    # Poll statistics to be included here later
    user_polls = Poll.objects.filter(creator=request.user).order_by('-created_at')
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        polls_list = polls_list.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        polls_list = polls_list.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(user_polls, 10)
    page_number = request.GET.get('page')
    polls = paginator.get_page(page_number)
    total_votes = sum(p.total_votes for p in user_polls)
    polls_remaining = 1 - user_polls.count() if not request.user.is_premium_active else None


    # Statistics
    total_polls = Poll.objects.filter(creator=request.user).count()
    active_polls = Poll.objects.filter(creator=request.user, status='active').count()
    total_votes = sum(poll.total_votes for poll in Poll.objects.filter(creator=request.user))

    context = {
        'title': 'Dashboard - PollSaaS',
        'user': user,
        'polls': user_polls,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_polls': total_polls,
        'active_polls': active_polls,
        'total_votes': total_votes,
        'polls_remaining': polls_remaining,
        'is_premium': request.user.is_premium,
        'max_polls': 50 if request.user.is_premium else 1,
    }
    return render(request, 'accounts/dashboard.html', context)


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
def contact_view(request):
    """
    Contact form view
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Show success message. Later, we will send emails.
            messages.success(
                request, 
                'Thank you for your message! We\'ll get back to you soon.'
            )
            return redirect('accounts:contact')
    else:
        form = ContactForm()
    
    context = {
        'title': 'Contact Us - PollSaaS',
        'form': form,
    }
    return render(request, 'accounts/contact.html', context)