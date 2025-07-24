from django.shortcuts import render

# Create your views here.
from django.shortcuts import redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView
from .forms import CustomUserCreationForm, CustomAuthenticationForm, ContactForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomSignUpView(CreateView):
    """
    User registration view
    """
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')
    
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
    context = {
        'title': 'Profile - PollSaaS',
        'user': user,
        'polls_remaining': user.polls_remaining,
        'is_premium': user.is_premium_active,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def dashboard_view(request):
    """
    User dashboard view
    """
    user = request.user
    # Poll statistics to be included here later
    context = {
        'title': 'Dashboard - PollSaaS',
        'user': user,
        'polls_created': user.polls_created,
        'polls_remaining': user.polls_remaining,
        'is_premium': user.is_premium_active,
        'total_votes': 0,  # Will calculate this later
    }
    return render(request, 'accounts/dashboard.html', context)

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