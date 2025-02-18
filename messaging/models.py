# messaging/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import now

User = get_user_model()

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    is_image = models.BooleanField(default=False)
    image = models.ImageField(upload_to="chat_images/", blank=True, null=True)
    image_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    original_content = models.TextField(null=True, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    def edit_message(self, new_content):
        if not self.original_content:
            self.original_content = self.content
        self.content = new_content
        self.edited_at = now()
        self.save()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = " (edited)" if self.edited_at else ""
        return f"{self.sender.username} -> {self.receiver.username}: {self.content}{status}"

class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    contact = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacted_by')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ['user', 'contact']

    def __str__(self):
        return f"{self.user.username} -> {self.contact.username}"

class UserStatus(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"