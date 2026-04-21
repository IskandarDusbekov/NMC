from django.urls import path

from .views import home_redirect

app_name = 'core'

urlpatterns = [
    path('', home_redirect, name='home'),
]
