from django.contrib import admin
from .models import Message, Room, Streak


admin.site.register(Message)
admin.site.register(Room)
admin.site.register(Streak)
