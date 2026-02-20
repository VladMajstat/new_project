from django.urls import path

from allauth.account import views as account_views
from allauth.account.views import LogoutView


urlpatterns = [
    path('login/', account_views.LoginView.as_view(), name='account_login'),
    path('signup/', account_views.SignupView.as_view(), name='account_signup'),
    path('logout/', LogoutView.as_view(), name='account_logout'),
]