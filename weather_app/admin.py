from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    User,
    City,
    WeatherData,
    WeatherForecast,
    SearchHistory,
    UserFavoriteLocation,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "phone_number", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "phone_number")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2", "first_name", "last_name", "phone_number"),
            },
        ),
    )


class WeatherDataInline(admin.TabularInline):
    model = WeatherData
    extra = 0
    fields = ("observed_at", "temperature_c", "humidity_pct", "wind_speed_ms", "description")
    readonly_fields = ()
    show_change_link = True


class WeatherForecastInline(admin.TabularInline):
    model = WeatherForecast
    extra = 0
    fields = ("forecast_time", "temp_min_c", "temp_max_c", "description")
    readonly_fields = ()
    show_change_link = True


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "country_code", "latitude", "longitude", "timezone_name")
    list_filter = ("country_code",)
    search_fields = ("name", "country_code")
    ordering = ("name", "country_code")
    inlines = [WeatherDataInline, WeatherForecastInline]


@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    list_display = (
        "city",
        "observed_at",
        "temperature_c",
        "humidity_pct",
        "pressure_hpa",
        "wind_speed_ms",
        "source",
    )
    list_filter = ("city", "source")
    search_fields = ("city__name", "city__country_code", "description")
    ordering = ("-observed_at",)
    date_hierarchy = "observed_at"
    autocomplete_fields = ("city",)


@admin.register(WeatherForecast)
class WeatherForecastAdmin(admin.ModelAdmin):
    list_display = ("city", "forecast_time", "temp_min_c", "temp_max_c", "source")
    list_filter = ("city", "source")
    search_fields = ("city__name", "city__country_code", "description")
    ordering = ("-forecast_time",)
    date_hierarchy = "forecast_time"
    autocomplete_fields = ("city",)


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "query", "matched_city", "searched_at")
    list_filter = ("searched_at",)
    search_fields = ("user__username", "user__email", "query", "matched_city__name")
    ordering = ("-searched_at",)
    date_hierarchy = "searched_at"
    autocomplete_fields = ("user", "matched_city")


@admin.register(UserFavoriteLocation)
class UserFavoriteLocationAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "added_at")
    list_filter = ("added_at",)
    search_fields = ("user__username", "user__email", "city__name", "city__country_code")
    ordering = ("-added_at",)
    autocomplete_fields = ("user", "city")
