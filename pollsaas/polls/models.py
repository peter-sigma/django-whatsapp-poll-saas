from django.db import models

# Create your models here.
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
import urllib.parse
import secrets
import string

User = get_user_model()

class Poll(models.Model):
    """
    Main Poll model for creating polls
    """
    POLL_TYPES = [
        ('single', 'Single Choice'),
        ('multiple', 'Multiple Choice'),
        ('rating', 'Rating Scale'),
        ('yes_no', 'Yes/No'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('closed', 'Closed'),
    ]

    title = models.CharField(
        max_length=200,
        verbose_name="Poll Title",
        help_text="Enter a clear, engaging title for your poll"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Optional: Add more context about your poll"
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_polls',
        verbose_name="Creator"
    )
    poll_type = models.CharField(
        max_length=20,
        choices=POLL_TYPES,
        default='single',
        verbose_name="Poll Type"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Status"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Uncheck to temporarily disable voting"
    )
    allow_multiple_votes = models.BooleanField(
        default=False,
        verbose_name="Allow Multiple Votes",
        help_text="Allow users to vote for multiple options"
    )
    require_login = models.BooleanField(
        default=False,
        verbose_name="Require Login",
        help_text="Require users to be logged in to vote"
    )
    show_results = models.BooleanField(
        default=True,
        verbose_name="Show Results",
        help_text="Show live results to voters"
    )
    allow_anonymous = models.BooleanField(
        default=True,
        verbose_name="Allow Anonymous Voting",
        help_text="Allow voting without registration"
    )
    
    # Timing fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expires At",
        help_text="Optional: Set when poll should automatically close"
    )
    
    # Unique identifier for sharing
    slug = models.SlugField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Unique URL identifier"
    )
    
    # Tracking fields
    total_votes = models.IntegerField(default=0)
    unique_voters = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Poll"
        verbose_name_plural = "Polls"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['creator', '-created_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['status', 'is_active']),
        ]
    
    def save(self, *args, **kwargs):
        # Generate unique slug if not provided
        if not self.slug:
            self.slug = self.generate_unique_slug()
        
        # Update status based on expiry
        if self.expires_at and timezone.now() > self.expires_at:
            self.status = 'expired'
            self.is_active = False
            
        super().save(*args, **kwargs)
    
    def generate_unique_slug(self):
        """Generate a unique random slug"""
        while True:
            slug = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
            if not Poll.objects.filter(slug=slug).exists():
                return slug
    
    @property
    def is_expired(self):
        """Check if poll has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def can_vote(self):
        """Check if voting is currently allowed"""
        return self.is_active and not self.is_expired and self.status == 'active'
    
    @property
    def days_remaining(self):
        """Calculate days remaining until expiry"""
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
    
    def get_absolute_url(self):
        """Get the poll detail URL"""
        return reverse('polls:poll_detail', kwargs={'slug': self.slug})
    
    def get_vote_url(self):
        """Get the public voting URL"""
        return reverse('polls:vote', kwargs={'slug': self.slug})
    
    def get_results_url(self):
        """Get the results URL"""
        return reverse('polls:results', kwargs={'slug': self.slug})
    
    def get_whatsapp_share_url(self):
        """Generate WhatsApp share URL"""
        poll_url = f"https://yoursite.com{self.get_vote_url()}"
        message = f"🗳️ Vote on: {self.title}\n{poll_url}"
        return f"https://wa.me/?text={urllib.parse.quote(message)}"
    
    def increment_vote_count(self):
        """Increment total vote count"""
        self.total_votes += 1
        self.save(update_fields=['total_votes'])
    
    def increment_voter_count(self):
        """Increment unique voter count"""
        self.unique_voters += 1
        self.save(update_fields=['unique_voters'])
    
    def __str__(self):
        return f"{self.title} ({self.get_poll_type_display()})"


class Choice(models.Model):
    """
    Individual choices for a poll
    """
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name="Poll"
    )
    text = models.CharField(
        max_length=200,
        verbose_name="Choice Text"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Optional: Add more details about this choice"
    )
    image = models.ImageField(
        upload_to='choice_images/',
        blank=True,
        null=True,
        verbose_name="Choice Image",
        help_text="Optional: Add an image for this choice"
    )
    votes = models.IntegerField(
        default=0,
        verbose_name="Vote Count"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Display Order"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Choice"
        verbose_name_plural = "Choices"
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['poll', 'order']),
        ]
    
    @property
    def vote_percentage(self):
        """Calculate percentage of votes for this choice"""
        if self.poll.total_votes == 0:
            return 0
        return round((self.votes / self.poll.total_votes) * 100, 1)
    
    def increment_votes(self):
        """Increment vote count for this choice"""
        self.votes += 1
        self.save(update_fields=['votes'])
    
    def __str__(self):
        return f"{self.text} ({self.votes} votes)"


class Vote(models.Model):
    """
    Individual vote record for tracking and preventing duplicates
    """
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name="Poll"
    )
    choice = models.ForeignKey(
        Choice,
        on_delete=models.CASCADE,
        related_name='vote_records',
        verbose_name="Choice"
    )
    voter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='votes',
        verbose_name="Voter",
        help_text="Registered user who voted (if logged in)"
    )
    voter_ip = models.GenericIPAddressField(
        verbose_name="Voter IP",
        help_text="IP address of the voter"
    )
    voter_session = models.CharField(
        max_length=40,
        blank=True,
        verbose_name="Session Key",
        help_text="Session key for anonymous voters"
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent",
        help_text="Browser information"
    )
    voted_at = models.DateTimeField(auto_now_add=True)
    
    # Additional tracking fields
    is_valid = models.BooleanField(
        default=True,
        verbose_name="Is Valid",
        help_text="Whether this vote is considered valid"
    )
    flagged_reason = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Flagged Reason",
        help_text="Reason if vote was flagged as suspicious"
    )
    
    class Meta:
        verbose_name = "Vote"
        verbose_name_plural = "Votes"
        ordering = ['-voted_at']
        indexes = [
            models.Index(fields=['poll', '-voted_at']),
            models.Index(fields=['voter_ip', 'poll']),
            models.Index(fields=['voter', 'poll']),
        ]
        
        # Constraints to prevent duplicate voting
        constraints = [
            models.UniqueConstraint(
                fields=['poll', 'voter'],
                condition=models.Q(voter__isnull=False),
                name='unique_registered_user_vote'
            ),
        ]
    
    def __str__(self):
        voter_info = self.voter.email if self.voter else f"Anonymous ({self.voter_ip})"
        return f"{voter_info} voted for '{self.choice.text}' in '{self.poll.title}'"


class PollAnalytics(models.Model):
    """
    Analytics data for polls (Premium feature)
    """
    poll = models.OneToOneField(
        Poll,
        on_delete=models.CASCADE,
        related_name='analytics',
        verbose_name="Poll"
    )
    
    # Time-based analytics
    votes_by_hour = models.JSONField(
        default=dict,
        verbose_name="Votes by Hour",
        help_text="Hourly vote distribution"
    )
    votes_by_day = models.JSONField(
        default=dict,
        verbose_name="Votes by Day",
        help_text="Daily vote distribution"
    )
    
    # Geographic data (if available)
    votes_by_country = models.JSONField(
        default=dict,
        verbose_name="Votes by Country",
        help_text="Country-wise vote distribution"
    )
    
    # Device/Platform analytics
    votes_by_device = models.JSONField(
        default=dict,
        verbose_name="Votes by Device",
        help_text="Device type distribution"
    )
    
    # Referrer analytics
    votes_by_referrer = models.JSONField(
        default=dict,
        verbose_name="Votes by Referrer",
        help_text="Traffic source distribution"
    )
    
    peak_voting_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Peak Voting Time"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Poll Analytics"
        verbose_name_plural = "Poll Analytics"
    
    def __str__(self):
        return f"Analytics for '{self.poll.title}'"