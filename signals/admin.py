from django.contrib import admin

from .models import DetectedItem, SignalKeyword, TrackedProduct, WatchSource


@admin.register(TrackedProduct)
class TrackedProductAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "aliases")
    ordering = ("name",)


@admin.register(WatchSource)
class WatchSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "is_active", "updated_at")
    list_filter = ("source_type", "is_active")
    search_fields = ("name", "url")
    ordering = ("-updated_at", "name")


@admin.register(SignalKeyword)
class SignalKeywordAdmin(admin.ModelAdmin):
    list_display = ("keyword", "score", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("keyword", "description")
    ordering = ("-score", "keyword")


@admin.register(DetectedItem)
class DetectedItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "product",
        "source",
        "total_score",
        "premium_probability",
        "google_trend_score",
        "social_buzz_score",
        "is_alert",
        "published_at",
        "created_at",
    )
    list_filter = ("is_alert", "source", "product")
    search_fields = (
        "title",
        "url",
        "summary",
        "matched_keywords",
        "prevalue_reason",
        "external_signal_summary",
    )
    ordering = ("-published_at", "-created_at")
