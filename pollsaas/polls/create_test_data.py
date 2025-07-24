#!/usr/bin/env python
"""
Test data creation script for PollSaaS - Day 5
Run this with: python manage.py shell < create_test_data.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pollsaas.settings')
django.setup()

from django.contrib.auth import get_user_model
from polls.models import Poll, Choice, Vote
from django.utils import timezone
from datetime import timedelta

User = get_user_model()
def create_test_data():
    """Create sample polls and choices for testing"""
    
    # Create test users
    print("Creating test users...")


    # Test user 2 (premium user)
    user2, created = User.objects.get_or_create(
        email='premiumuser@example.com',
        defaults={
            'username': 'premiumuser',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'is_premium': True,
            'premium_until': timezone.now() + timedelta(days=30),
            'polls_created': 5
        }
    )
    if created:
        user2.set_password('testpass123')
        user2.save()
        print(f"Created premium user: {user2.email}")

    # # Test user 1 (free user)
    # user1, created = User.objects.get_or_create(
    #     email='testuser1@example.com',
    #     defaults={
    #         'username': 'testuser1',
    #         'first_name': 'John',
    #         'last_name': 'Doe',
    #         'is_premium': False,
    #         'polls_created': 0
    #     }
    # )
    # if created:
    #     user1.set_password('testpass123')
    #     user1.save()
    #     print(f"Created free user: {user1.email}")
    
    
    