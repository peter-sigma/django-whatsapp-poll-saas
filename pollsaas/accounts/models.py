from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CustomUser(AbstractUser):
    """
    Custom User model for PollSaaS
    Extends Django's built-in User model with additional fields for our SaaS
    """
    email = models.EmailField(unique=True, verbose_name="Email Address")
    is_premium = models.BooleanField(
        default=False, 
        verbose_name="Premium User",
        help_text="Designates whether this user has premium access."
    )
    polls_created = models.IntegerField(
        default=0,
        verbose_name="Polls Created",
        help_text="Number of polls this user has created."
    )
    premium_until = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Premium Valid Until",
        help_text="Date until which premium access is valid."
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Stripe Customer ID",
        help_text="Stripe customer ID for billing."
    )
    date_joined = models.DateTimeField(default=timezone.now)
    
    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        
    @property
    def is_premium_active(self):
        """Check if premium subscription is currently active"""
        if not self.is_premium:
            return False
        if self.premium_until is None:
            return True
        return timezone.now() < self.premium_until
    
    @property
    def polls_remaining(self):
        """Calculate how many polls user can still create"""
        if self.is_premium_active:
            return float('inf')  # Unlimited for premium users
        return max(0, 1 - self.polls_created)  # Free users get 1 poll
    
    def can_create_poll(self):
        """Check if user can create a new poll"""
        return self.is_premium_active or self.polls_created < 1
    
    def increment_poll_count(self):
        """Increment the user's poll count"""
        self.polls_created += 1
        self.save(update_fields=['polls_created'])
        
    def __str__(self):
        return self.email