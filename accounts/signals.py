from django.db.models.signals import pre_save, post_save
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from .models import Profile

User = get_user_model()

def generate_unique_username(email):
    """Generate a unique username from email."""
    base_username = email.split("@")[0].replace(".", "_")  # Convert `.` to `_`
    username = base_username
    count = 1

    # Ensure username is unique
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{count}"
        count += 1

    return username


# @receiver(pre_save, sender=User)
# def set_username(sender, instance, **kwargs):
#     """Automatically generate a username before saving a new user"""
#     if not instance.username:  # Only set username if it's not already provided
#         instance.username = generate_unique_username(instance.email)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance when a new User is created"""
    if created:
        Profile.objects.get_or_create(user=instance)