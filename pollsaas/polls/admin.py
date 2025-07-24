from django.contrib import admin

# Register your models here.
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Poll, Choice, Vote, PollAnalytics


class ChoiceInline(admin.TabularInline):
    """Inline admin for Poll choices"""
    model = Choice
    extra = 3
    fields = ('text', 'description', 'order', 'is_active', 'votes')
    readonly_fields = ('votes',)
    ordering = ('order',)


class VoteInline(admin.TabularInline):
    """Inline admin for Poll votes (read-only)"""
    model = Vote
    extra = 0
    max_num = 0
    fields = ('choice', 'voter', 'voter_ip', 'voted_at', 'is_valid')
    readonly_fields = ('choice', 'voter', 'voter_ip', 'voted_at', 'is_valid')
    ordering = ('-voted_at',)
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    """Admin interface for Poll model"""
    list_display = (
        'title', 
        'creator', 
        'poll_type', 
        'status',
        'total_votes',
        'unique_voters',
        'is_active',
        'created_at',
        'expires_at',
        'view_poll_link'
    )
    list_filter = (
        'poll_type',
        'status', 
        'is_active',
        'allow_multiple_votes',
        'require_login',
        'created_at',
        'expires_at'
    )
    search_fields = ('title', 'description', 'creator__email', 'creator__username')
    readonly_fields = (
        'slug',
        'total_votes',
        'unique_voters',
        'created_at',
        'updated_at',
        'whatsapp_share_url',
        'poll_urls'
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title',
                'description',
                'creator',
                'poll_type',
                'status'
            )
        }),
        ('Settings', {
            'fields': (
                'is_active',
                'allow_multiple_votes',
                'require_login',
                'show_results',
                'allow_anonymous',
                'expires_at'
            )
        }),
        ('URLs & Sharing', {
            'fields': (
                'slug',
                'poll_urls',
                'whatsapp_share_url'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'total_votes',
                'unique_voters',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ChoiceInline, VoteInline]
    
    actions = ['activate_polls', 'deactivate_polls', 'close_polls']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('creator')
    
    def view_poll_link(self, obj):
        """Create a link to view the poll"""
        if obj.slug:
            url = reverse('polls:vote', kwargs={'slug': obj.slug})
            return format_html('<a href="{}" target="_blank">View Poll</a>', url)
        return "No slug"
    view_poll_link.short_description = "View Poll"
    
    def poll_urls(self, obj):
        """Display poll URLs"""
        if obj.slug:
            vote_url = f"/vote/{obj.slug}/"
            results_url = f"/results/{obj.slug}/"
            return format_html(
                '<strong>Vote:</strong> <a href="{}" target="_blank">{}</a><br>'
                '<strong>Results:</strong> <a href="{}" target="_blank">{}</a>',
                vote_url, vote_url, results_url, results_url
            )
        return "No URLs available"
    poll_urls.short_description = "Poll URLs"
    
    def whatsapp_share_url(self, obj):
        """Display WhatsApp share URL"""
        if obj.slug:
            url = obj.get_whatsapp_share_url()
            return format_html('<a href="{}" target="_blank">WhatsApp Share Link</a>', url)
        return "No share URL"
    whatsapp_share_url.short_description = "WhatsApp Share"
    
    def activate_polls(self, request, queryset):
        """Bulk action to activate polls"""
        updated = queryset.update(is_active=True, status='active')
        self.message_user(request, f'{updated} polls were activated.')
    activate_polls.short_description = "Activate selected polls"
    
    def deactivate_polls(self, request, queryset):
        """Bulk action to deactivate polls"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} polls were deactivated.')
    deactivate_polls.short_description = "Deactivate selected polls"
    
    def close_polls(self, request, queryset):
        """Bulk action to close polls"""
        updated = queryset.update(status='closed', is_active=False)
        self.message_user(request, f'{updated} polls were closed.')
    close_polls.short_description = "Close selected polls"


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    """Admin interface for Choice model"""
    list_display = (
        'text',
        'poll',
        'votes',
        'vote_percentage_display',
        'order',
        'is_active',
        'created_at'
    )
    list_filter = (
        'is_active',
        'created_at',
        'poll__poll_type',
        'poll__creator'
    )
    search_fields = ('text', 'description', 'poll__title')
    readonly_fields = ('votes', 'created_at', 'vote_percentage_display')
    
    fieldsets = (
        ('Choice Information', {
            'fields': ('poll', 'text', 'description', 'image')
        }),
        ('Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Statistics', {
            'fields': ('votes', 'vote_percentage_display', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('poll')
    
    def vote_percentage_display(self, obj):
        """Display vote percentage with visual bar"""
        percentage = obj.vote_percentage
        if percentage > 0:
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
                '<div style="width: {}%; background-color: #28a745; height: 20px; '
                'border-radius: 3px; text-align: center; color: white; font-size: 12px; '
                'line-height: 20px;">{:.1f}%</div></div>',
                percentage, percentage
            )
        return "0%"
    vote_percentage_display.short_description = "Vote %"


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    """Admin interface for Vote model"""
    list_display = (
        'poll',
        'choice',
        'voter_display',
        'voter_ip',
        'voted_at',
        'is_valid',
        'flagged_reason'
    )
    list_filter = (
        'is_valid',
        'voted_at',
        'poll__poll_type',
        'poll__creator',
        'flagged_reason'
    )
    search_fields = (
        'poll__title',
        'choice__text',
        'voter__email',
        'voter_ip',
        'flagged_reason'
    )
    readonly_fields = (
        'poll',
        'choice',
        'voter',
        'voter_ip',
        'voter_session',
        'user_agent',
        'voted_at'
    )
    
    fieldsets = (
        ('Vote Information', {
            'fields': ('poll', 'choice', 'voter', 'voted_at')
        }),
        ('Tracking Information', {
            'fields': ('voter_ip', 'voter_session', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Validation', {
            'fields': ('is_valid', 'flagged_reason')
        })
    )
    
    actions = ['mark_as_valid', 'mark_as_invalid', 'flag_suspicious']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'poll', 'choice', 'voter'
        )
    
    def voter_display(self, obj):
        """Display voter information"""
        if obj.voter:
            return f"{obj.voter.email} (Registered)"
        return f"Anonymous"
    voter_display.short_description = "Voter"
    
    def has_add_permission(self, request):
        """Prevent adding votes through admin"""
        return False
    
    def mark_as_valid(self, request, queryset):
        """Mark selected votes as valid"""
        updated = queryset.update(is_valid=True, flagged_reason='')
        self.message_user(request, f'{updated} votes marked as valid.')
    mark_as_valid.short_description = "Mark as valid"
    
    def mark_as_invalid(self, request, queryset):
        """Mark selected votes as invalid"""
        updated = queryset.update(is_valid=False)
        self.message_user(request, f'{updated} votes marked as invalid.')
    mark_as_invalid.short_description = "Mark as invalid"
    
    def flag_suspicious(self, request, queryset):
        """Flag votes as suspicious"""
        updated = queryset.update(
            is_valid=False, 
            flagged_reason='Admin flagged as suspicious'
        )
        self.message_user(request, f'{updated} votes flagged as suspicious.')
    flag_suspicious.short_description = "Flag as suspicious"


@admin.register(PollAnalytics)
class PollAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for Poll Analytics"""
    list_display = (
        'poll',
        'total_votes_display',
        'peak_voting_time',
        'updated_at'
    )
    list_filter = (
        'created_at',
        'updated_at',
        'poll__poll_type'
    )
    search_fields = ('poll__title',)
    readonly_fields = (
        'poll',
        'votes_by_hour',
        'votes_by_day',
        'votes_by_country',
        'votes_by_device',
        'votes_by_referrer',
        'peak_voting_time',
        'created_at',
        'updated_at'
    )
    
    fieldsets = (
        ('Poll Information', {
            'fields': ('poll',)
        }),
        ('Time Analytics', {
            'fields': ('votes_by_hour', 'votes_by_day', 'peak_voting_time'),
            'classes': ('collapse',)
        }),
        ('Geographic Analytics', {
            'fields': ('votes_by_country',),
            'classes': ('collapse',)
        }),
        ('Technical Analytics', {
            'fields': ('votes_by_device', 'votes_by_referrer'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def total_votes_display(self, obj):
        """Display total votes for the poll"""
        return obj.poll.total_votes
    total_votes_display.short_description = "Total Votes"
    
    def has_add_permission(self, request):
        """Prevent manual creation of analytics"""
        return False


# Custom admin site configuration
admin.site.site_header = "PollSaaS Administration"
admin.site.site_title = "PollSaaS Admin"
admin.site.index_title = "Welcome to PollSaaS Administration"