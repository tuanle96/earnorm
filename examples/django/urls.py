"""Django example URL configuration."""

from django.urls import path
from views import PostView, UserPostView, UserView

urlpatterns = [
    # User endpoints
    path("users/", UserView.as_view(), name="user-list"),
    path("users/<str:user_id>/", UserView.as_view(), name="user-detail"),
    path("users/<str:user_id>/posts/", UserPostView.as_view(), name="user-posts"),
    # Post endpoints
    path("posts/", PostView.as_view(), name="post-list"),
    path("posts/<str:post_id>/", PostView.as_view(), name="post-detail"),
]
