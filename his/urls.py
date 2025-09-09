from django.urls import path

from . import views

urlpatterns = [
    path("userLog/", views.userhis, name="userLog"),
]