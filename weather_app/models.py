from dataclasses import fields
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone


class User(AbstractUser):
    """Người dùng tùy chỉnh kế thừa từ AbstractUser của Django."""

    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self) -> str:
        return self.username


class City(models.Model):
    """Thông tin địa điểm (thành phố)."""

    name = models.CharField(max_length=120)
    country_code = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2")
    latitude = models.DecimalField(max_digits=8, decimal_places=5)
    longitude = models.DecimalField(max_digits=8, decimal_places=5)
    timezone_name = models.CharField(max_length=64, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "City"
        verbose_name = "City"
        verbose_name_plural = "Cities"
        indexes = [
            models.Index(fields=["name", "country_code"]),
            models.Index(fields=["latitude", "longitude"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'country_code', 'latitude', 'longitude'],
                name="unique_city"
            )
        ]

    def __str__(self) -> str:
        return f"{self.name}, {self.country_code}"


class WeatherData(models.Model):
    """Dữ liệu thời tiết hiện tại cho một địa điểm."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="current_weathers")
    observed_at = models.DateTimeField(default=timezone.now)

    temperature_c = models.DecimalField(max_digits=5, decimal_places=2)
    humidity_pct = models.PositiveSmallIntegerField()
    pressure_hpa = models.PositiveIntegerField()
    wind_speed_ms = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=120, blank=True, null=True)
    icon_code = models.CharField(max_length=10, blank=True, null=True)
    source = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "WeatherData"
        indexes = [
            models.Index(fields=["city", "observed_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["city", "observed_at"],
                name="unique_weather_data"
            )
        ]

    def __str__(self) -> str:
        return f"{self.city} @ {self.observed_at:%Y-%m-%d %H:%M}"


class WeatherForecast(models.Model):
    """Dự báo thời tiết theo mốc thời gian cho một địa điểm."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="forecasts")
    forecast_time = models.DateTimeField()

    temp_min_c = models.DecimalField(max_digits=5, decimal_places=2)
    temp_max_c = models.DecimalField(max_digits=5, decimal_places=2)
    precipitation_probability_pct = models.PositiveSmallIntegerField(blank=True, null=True)
    description = models.CharField(max_length=120, blank=True, null=True)
    icon_code = models.CharField(max_length=10, blank=True, null=True)
    source = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "WeatherForecast"
        indexes = [
            models.Index(fields=["city", "forecast_time"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["city", "forecast_time"],
                name="unique_weather_forecast"
            )
        ]

    def __str__(self) -> str:
        return f"Forecast {self.city} @ {self.forecast_time:%Y-%m-%d %H:%M}"


class SearchHistory(models.Model):
    """Lịch sử tìm kiếm của người dùng."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_histories")
    query = models.CharField(max_length=120)
    matched_city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name="search_matches")
    searched_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "SearchHistory"
        verbose_name = "Search History"
        verbose_name_plural = "Search Histories"
        ordering = ["-searched_at"]
        indexes = [
            models.Index(fields=["user", "searched_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} searched '{self.query}'"


class UserFavoriteLocation(models.Model):
    """Địa điểm yêu thích của người dùng."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_locations")
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="favorited_by")
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "UserFavoriteLocation"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "city"],
                name="unique_user_favorite_location"
            )
        ]
        indexes = [
            models.Index(fields=["user", "city"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} ❤ {self.city}"