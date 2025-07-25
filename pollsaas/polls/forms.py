from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Poll, Choice

User = get_user_model()


class PollCreateForm(forms.ModelForm):
    """
    Main form for creating polls with dynamic choices
    """
    choices = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 6,
            'placeholder': 'Enter each choice on a new line\nExample:\nOption A\nOption B\nOption C',
            'class': 'form-control'
        }),
        help_text="Enter each choice on a new line (minimum 2 choices required)",
        label="Poll Choices"
    )
    
    expires_in_days = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=365,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 7'
        }),
        help_text="Optional: Number of days until poll expires (leave empty for no expiry)",
        label="Expires in (days)"
    )
    
    class Meta:
        model = Poll
        fields = [
            'title', 
            'description', 
            'poll_type', 
            'allow_multiple_votes',
            'require_login',
            'show_results',
            'allow_anonymous'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your poll question...',
                'maxlength': 200
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional: Add more context about your poll...'
            }),
            'poll_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'allow_multiple_votes': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'require_login': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'show_results': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'allow_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        help_texts = {
            'title': 'Make it clear and engaging (max 200 characters)',
            'description': 'Optional: Provide additional context or instructions',
            'poll_type': 'Choose how users can vote',
            'allow_multiple_votes': 'Allow voters to select multiple options',
            'require_login': 'Require users to be logged in to vote',
            'show_results': 'Show live results to voters after they vote',
            'allow_anonymous': 'Allow voting without user registration',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Check if user has premium features
        if self.user and not self.user.is_premium:
            # Limit poll types for free users
            self.fields['poll_type'].choices = [
                ('single', 'Single Choice'),
                ('yes_no', 'Yes/No'),
            ]
            # Disable premium features
            self.fields['require_login'].widget.attrs['disabled'] = True
            self.fields['require_login'].help_text = "Premium feature - upgrade to enable"
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title or len(title.strip()) < 5:
            raise forms.ValidationError("Poll title must be at least 5 characters long.")
        return title.strip()
    
    def clean_choices(self):
        choices_text = self.cleaned_data.get('choices', '')
        if not choices_text:
            raise forms.ValidationError("You must provide at least 2 choices.")
        
        # Split by lines and clean up
        choices = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]
        
        # Validate minimum choices
        if len(choices) < 2:
            raise forms.ValidationError("You must provide at least 2 choices.")
        
        # Validate maximum choices (free vs premium)
        max_choices = 10 if (self.user and self.user.is_premium) else 5
        if len(choices) > max_choices:
            raise forms.ValidationError(
                f"Maximum {max_choices} choices allowed. "
                f"{'Upgrade to premium for up to 10 choices.' if not (self.user and self.user.is_premium) else ''}"
            )
        
        # Validate individual choice length
        for i, choice in enumerate(choices, 1):
            if len(choice) > 200:
                raise forms.ValidationError(f"Choice {i} is too long (max 200 characters).")
            if len(choice) < 1:
                raise forms.ValidationError(f"Choice {i} cannot be empty.")
        
        # Check for duplicate choices
        if len(choices) != len(set(choices)):
            raise forms.ValidationError("Duplicate choices are not allowed.")
        
        return choices
    
    def clean_expires_in_days(self):
        expires_in_days = self.cleaned_data.get('expires_in_days')
        if expires_in_days:
            # Check if user can set expiry (premium feature for long expiry)
            if expires_in_days > 30 and (not self.user or not self.user.is_premium):
                raise forms.ValidationError("Free users can set expiry up to 30 days. Upgrade for longer polls.")
        return expires_in_days
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate poll type specific settings
        poll_type = cleaned_data.get('poll_type')
        allow_multiple_votes = cleaned_data.get('allow_multiple_votes')
        
        if poll_type == 'yes_no' and allow_multiple_votes:
            raise forms.ValidationError("Yes/No polls cannot allow multiple votes.")
        
        # Check user's poll creation limits
        if self.user:
            user_polls = Poll.objects.filter(creator=self.user).count()
            max_polls = 50 if self.user.is_premium else 1
            
            if user_polls >= max_polls:
                raise forms.ValidationError(
                    f"You have reached your poll limit ({max_polls} polls). "
                    f"{'Delete some polls to create new ones.' if self.user.is_premium else 'Upgrade to premium for unlimited polls.'}"
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        poll = super().save(commit=False)
        
        if self.user:
            poll.creator = self.user
        
        # Set expiry date if provided
        expires_in_days = self.cleaned_data.get('expires_in_days')
        if expires_in_days:
            poll.expires_at = timezone.now() + timedelta(days=expires_in_days)
        
        # Set initial status
        poll.status = 'active'
        poll.is_active = True
        
        if commit:
            poll.save()
            
            # Create choices
            choices = self.cleaned_data.get('choices', [])
            for i, choice_text in enumerate(choices):
                Choice.objects.create(
                    poll=poll,
                    text=choice_text,
                    order=i
                )
            
            # Update user's poll count
            if self.user:
                self.user.polls_created += 1
                self.user.save(update_fields=['polls_created'])
        
        return poll


class PollEditForm(forms.ModelForm):
    """
    Form for editing existing polls (limited editing after votes are cast)
    """
    class Meta:
        model = Poll
        fields = [
            'title',
            'description', 
            'is_active',
            'show_results',
            'expires_at'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'show_results': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If poll has votes, limit what can be edited
        if self.instance and self.instance.total_votes > 0:
            # Disable critical fields that shouldn't change after voting starts
            self.fields['title'].widget.attrs['readonly'] = True
            self.fields['title'].help_text = "Cannot be changed after voting has started"
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if self.instance and self.instance.total_votes > 0:
            # Don't allow title changes if there are votes
            if title != self.instance.title:
                raise forms.ValidationError("Cannot change title after voting has started.")
        return title


class QuickPollForm(forms.Form):
    """
    Quick poll creation form for simple yes/no or single choice polls
    """
    question = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ask your question...'
        }),
        label="Your Question"
    )
    
    poll_type = forms.ChoiceField(
        choices=[
            ('yes_no', 'Yes/No'),
            ('single', 'Multiple Choice'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        initial='yes_no',
        label="Poll Type"
    )
    
    # Only shown for multiple choice
    option_1 = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Option 1'
        })
    )
    
    option_2 = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Option 2'
        })
    )
    
    option_3 = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Option 3 (optional)'
        })
    )
    
    expires_in_hours = forms.ChoiceField(
        choices=[
            ('', 'No expiry'),
            ('1', '1 hour'),
            ('6', '6 hours'),
            ('24', '1 day'),
            ('168', '1 week'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Expires in"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        poll_type = cleaned_data.get('poll_type')
        
        if poll_type == 'single':
            option_1 = cleaned_data.get('option_1')
            option_2 = cleaned_data.get('option_2')
            
            if not option_1 or not option_2:
                raise forms.ValidationError("Multiple choice polls need at least 2 options.")
        
        return cleaned_data
    
    def create_poll(self, user):
        """Create a poll from the quick form data"""
        cleaned_data = self.cleaned_data
        
        # Create poll
        poll = Poll.objects.create(
            title=cleaned_data['question'],
            creator=user,
            poll_type=cleaned_data['poll_type'],
            status='active',
            is_active=True,
            allow_anonymous=True,
            show_results=True
        )
        
        # Set expiry if provided
        expires_in_hours = cleaned_data.get('expires_in_hours')
        if expires_in_hours:
            poll.expires_at = timezone.now() + timedelta(hours=int(expires_in_hours))
            poll.save()
        
        # Create choices
        if cleaned_data['poll_type'] == 'yes_no':
            Choice.objects.create(poll=poll, text='Yes', order=0)
            Choice.objects.create(poll=poll, text='No', order=1)
        else:
            # Multiple choice
            choices = [
                cleaned_data.get('option_1'),
                cleaned_data.get('option_2'),
                cleaned_data.get('option_3'),
            ]
            for i, choice_text in enumerate(choices):
                if choice_text:
                    Choice.objects.create(poll=poll, text=choice_text, order=i)
        
        # Update user's poll count
        user.polls_created += 1
        user.save(update_fields=['polls_created'])
        
        return poll