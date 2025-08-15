from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .services import WeatherService, EmailService

# Create your views here.

@require_GET
def current_weather(request):
    city = request.GET.get('city', '').strip()
    if not city:
        return JsonResponse({'error': 'Missing city'}, status=400)

    data = WeatherService.get_current_weather(city)
    if request.user.is_authenticated:
        WeatherService.save_search_history(request.user, query=city, matched_city=None)

    if data is None:
        return JsonResponse({'error': 'Weather not found'}, status=404)
    return JsonResponse(data)

@require_GET
def weather_forecast(request):
    city = request.GET.get('city', '').strip()
    if not city:
        return JsonResponse({'error': 'Missing city'}, status=400)

    items = WeatherService.get_weather_forecast(city)
    if request.user.is_authenticated:
        WeatherService.save_search_history(request.user, query=city, matched_city=None)

    return JsonResponse({'forecasts': items})

@require_GET
def search_history(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        limit = int(request.GET.get('limit', '10'))
    except ValueError:
        limit = 10
    limit = max(1, min(limit, 50))

    histories = WeatherService.get_user_search_history(request.user, limit=limit)
    payload = []
    for h in histories:
        matched = f"{h.matched_city.name}, {h.matched_city.country_code}" if h.matched_city else None
        payload.append({
            'query': h.query,
            'matched_city': matched,
            'searched_at': h.searched_at.isoformat(),
        })
    return JsonResponse({'history': payload})

