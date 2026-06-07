from django.contrib import admin

from .models import DetectedItem, SignalKeyword, WatchSource


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
    list_display = ("title", "source", "total_score", "is_alert", "published_at", "created_at")
    list_filter = ("is_alert", "source")
    search_fields = ("title", "url", "summary", "matched_keywords")
    ordering = ("-published_at", "-created_at")
