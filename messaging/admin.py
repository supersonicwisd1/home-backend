from django.contrib import admin
from .models import Message, Contact, UserStatus

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id",)
    pass

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id",)
    pass

@admin.register(UserStatus)
class UserStatusAdmin(admin.ModelAdmin):
    pass