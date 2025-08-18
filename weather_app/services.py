import logging
from datetime import datetime, time as dt_time, timezone as dt_timezone
from typing import Optional
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
import requests
from django.conf import settings

from .models import City, WeatherData, WeatherForecast, SearchHistory, UserFavoriteLocation

logger = logging.getLogger(__name__)


class WeatherService:
    """Service xử lý logic nghiệp vụ thời tiết"""

    @staticmethod
    def _get_or_create_city(
        name: str,
        country_code: str,
        latitude: float,
        longitude: float,
        timezone_name: Optional[str] = None,
    ) -> City:
        """Lấy hoặc tạo `City` từ dữ liệu API.

        Ưu tiên nhận diện theo bộ (name, country_code, latitude, longitude) do ràng buộc unique_together.
        """
        city_obj, _ = City.objects.get_or_create(
            name=name,
            country_code=country_code,
            latitude=latitude,
            longitude=longitude,
            defaults={"timezone_name": timezone_name},
        )
        return city_obj
    
    @staticmethod
    def get_current_weather(city):
        """Lấy thời tiết hiện tại từ API"""
        try:
            url = f"{settings.WEATHER_API_URL}/weather"
            params = {
                'q': city,
                'appid': settings.WEATHER_API_KEY,
                'units': 'metric'
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Tạo/tìm City
                city_obj = WeatherService._get_or_create_city(
                    name=data['name'],
                    country_code=data['sys']['country'],
                    latitude=data['coord']['lat'],
                    longitude=data['coord']['lon'],
                )

                # Thời điểm quan trắc theo UTC từ API
                observed_at = datetime.fromtimestamp(data.get('dt', int(datetime.now(tz=dt_timezone.utc).timestamp())), tz=dt_timezone.utc)

                # Map đúng field theo model WeatherData
                weather_record_fields = {
                    'city': city_obj,
                    'observed_at': observed_at,
                    'temperature_c': data['main']['temp'],
                    'humidity_pct': data['main']['humidity'],
                    'pressure_hpa': data['main']['pressure'],
                    'wind_speed_ms': data['wind'].get('speed', 0),
                    'description': data['weather'][0]['description'],
                    'icon_code': data['weather'][0]['icon'],
                    'source': 'openweather',
                }

                WeatherData.objects.create(**weather_record_fields)

                # Trả về gói dữ liệu thân thiện cho UI
                return {
                    'city': f"{city_obj.name}, {city_obj.country_code}",
                    'observed_at': observed_at.isoformat(),
                    'temperature_c': weather_record_fields['temperature_c'],
                    'humidity_pct': weather_record_fields['humidity_pct'],
                    'pressure_hpa': weather_record_fields['pressure_hpa'],
                    'wind_speed_ms': weather_record_fields['wind_speed_ms'],
                    'description': weather_record_fields['description'],
                    'icon_code': weather_record_fields['icon_code'],
                }
            else:
                return None
        except Exception as e:
            logger.exception("Error fetching weather data")
            return None
    
    @staticmethod
    def get_weather_forecast(city: str):
        """Lấy dự báo thời tiết (tổng hợp theo ngày từ API 3h/5 ngày)."""
        try:
            url = f"{settings.WEATHER_API_URL}/forecast"
            params = {
                'q': city,
                'appid': settings.WEATHER_API_KEY,
                'units': 'metric'
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                city_payload = data['city']
                city_obj = WeatherService._get_or_create_city(
                    name=city_payload['name'],
                    country_code=city_payload['country'],
                    latitude=city_payload['coord']['lat'],
                    longitude=city_payload['coord']['lon'],
                )
                
                forecast_data = []
                daily_data = {}
                
                for item in data['list']:
                    point_dt = datetime.fromtimestamp(item['dt'], tz=dt_timezone.utc)
                    date_key = point_dt.date()
                    temp_val = item['main']['temp']
                    humidity_val = item['main'].get('humidity')
                    pop_val = item.get('pop')  # 0..1
                    description_val = item['weather'][0]['description']
                    icon_val = item['weather'][0]['icon']

                    if date_key not in daily_data:
                        daily_data[date_key] = {
                            'temps': [temp_val],
                            'humidities': [h for h in [humidity_val] if h is not None],
                            'pops': [p for p in [pop_val] if p is not None],
                            'description_counts': {description_val: 1},
                            'icon_counts': {icon_val: 1},
                        }
                    else:
                        bucket = daily_data[date_key]
                        bucket['temps'].append(temp_val)
                        if humidity_val is not None:
                            bucket['humidities'].append(humidity_val)
                        if pop_val is not None:
                            bucket['pops'].append(pop_val)
                        bucket['description_counts'][description_val] = bucket['description_counts'].get(description_val, 0) + 1
                        bucket['icon_counts'][icon_val] = bucket['icon_counts'].get(icon_val, 0) + 1
                
                # Tạo dữ liệu dự báo theo ngày (tối đa 5 ngày theo API này)
                for date_key in sorted(daily_data.keys())[:5]:
                    bucket = daily_data[date_key]

                    # Chọn 12:00 UTC làm thời điểm đại diện
                    forecast_time = datetime.combine(date_key, dt_time(hour=12, tzinfo=dt_timezone.utc))

                    # Tính toán các đại lượng
                    temp_min_c = min(bucket['temps'])
                    temp_max_c = max(bucket['temps'])
                    pop_pct = None
                    if bucket['pops']:
                        pop_pct = int(round(100 * (sum(bucket['pops']) / len(bucket['pops']))))

                    # Chọn mô tả/icon phổ biến nhất
                    description = max(bucket['description_counts'].items(), key=lambda kv: kv[1])[0]
                    icon_code = max(bucket['icon_counts'].items(), key=lambda kv: kv[1])[0]

                    defaults = {
                        'temp_min_c': temp_min_c,
                        'temp_max_c': temp_max_c,
                        'precipitation_probability_pct': pop_pct,
                        'description': description,
                        'icon_code': icon_code,
                        'source': 'openweather',
                    }

                    WeatherForecast.objects.update_or_create(
                        city=city_obj,
                        forecast_time=forecast_time,
                        defaults=defaults,
                    )

                    forecast_data.append({
                        'city': f"{city_obj.name}, {city_obj.country_code}",
                        'forecast_time': forecast_time.isoformat(),
                        'temp_min_c': temp_min_c,
                        'temp_max_c': temp_max_c,
                        'precipitation_probability_pct': pop_pct,
                        'description': description,
                        'icon_code': icon_code,
                    })
                
                return forecast_data
            else:
                return []
        except Exception as e:
            logger.exception("Error fetching forecast data")
            return []
    
    @staticmethod
    def save_search_history(user, query: str, matched_city: Optional[City] = None):
        """Lưu lịch sử tìm kiếm theo model hiện tại.

        - `query`: chuỗi người dùng nhập
        - `matched_city`: tham chiếu `City` nếu đã xác định được
        """
        if user and getattr(user, "is_authenticated", False):
            SearchHistory.objects.create(
                user=user,
                query=query,
                matched_city=matched_city,
            )
    
    @staticmethod
    def get_user_search_history(user, limit=10):
        """Lấy lịch sử tìm kiếm của user"""
        if user.is_authenticated:
            return SearchHistory.objects.filter(user=user)[:limit]
        return []

class EmailService:
    """Service xử lý gửi email"""
    
    @staticmethod
    def send_verification_email(user):
        """Gửi email xác thực"""
        try:
            # Tạo token
            token = user.generate_email_verification_token()
            
            # Email context
            context = {
                'user': user,
                'token': token,
                'site_url': settings.SITE_URL,
                'expires_hours': 24
            }
            
            # Render email template
            subject = 'Weather App - Xác thực email của bạn'
            html_message = render_to_string('emails/verify_email.html', context)
            plain_message = strip_tags(html_message)
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Verification email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            return False
