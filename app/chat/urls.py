from unicodedata import name
from django.urls import path

from . import views

urlpatterns = [
    path('<str:room_name>/', views.room, name='room'),
]
