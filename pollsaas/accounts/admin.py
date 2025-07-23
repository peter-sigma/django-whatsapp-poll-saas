from django.contrib import admin

# Register your models here.
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin interface for our User model
    """
    list_display = (
        'email', 'username', 'is_premium', 'polls_created', 
        'date_joined', 'is_staff', 'is_active'
    )
    list_filter = (
        'is_premium', 'is_staff', 'is_active', 'date_joined'
    )
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    # Fields to show when editing a user
    fieldsets = UserAdmin.fieldsets + (
        ('PollSaaS Info', {
            'fields': (
                'is_premium', 'polls_created', 'premium_until', 
                'stripe_customer_id'
            )
        }),
    )
    
    # Fields to show when adding a new user
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('PollSaaS Info', {
            'fields': ('email', 'is_premium')
        }),
    )
    
    # Make email field required
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # Adding new user
            form.base_fields['email'].required = True
        return form
    
    # Custom actions
    actions = ['make_premium', 'remove_premium', 'reset_poll_count']
    
    def make_premium(self, request, queryset):
        """Make selected users premium"""
        updated = queryset.update(is_premium=True)
        self.message_user(
            request, 
            f'{updated} users were successfully made premium.'
        )
    make_premium.short_description = 'Make selected users premium'
    
    def remove_premium(self, request, queryset):
        """Remove premium from selected users"""
        updated = queryset.update(is_premium=False, premium_until=None)
        self.message_user(
            request, 
            f'{updated} users had their premium status removed.'
        )
    remove_premium.short_description = 'Remove premium from selected users'
    
    def reset_poll_count(self, request, queryset):
        """Reset poll count for selected users"""
        updated = queryset.update(polls_created=0)
        self.message_user(
            request, 
            f'Poll count reset for {updated} users.'
        )
    reset_poll_count.short_description = 'Reset poll count for selected users'