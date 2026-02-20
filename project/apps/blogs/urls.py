from django.urls import path

from . import views


urlpatterns = [
    path('detail/<int:pk>', views.blog_detail, name='blog_detail'),
    path('', views.blog_list, name='blogs_list'),
    path('category/<str:category>', views.blog_list, name='blogs_list'),
]