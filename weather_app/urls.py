from django.urls import path
from . import views

urlpatterns = [
    path('api/weather/current', views.current_weather, name='current_weather'),
    path('api/weather/forecast', views.weather_forecast, name='weather_forecast'),
    path('api/search/history', views.search_history, name='search_history'),
]