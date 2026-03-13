from django.contrib import admin

from .models import WatchStock


@admin.register(WatchStock)
class WatchStockAdmin(admin.ModelAdmin):
    list_display = ("ticker", "name", "market", "is_active", "updated_at")
    list_filter = ("is_active", "market")
    search_fields = ("ticker", "name")
    ordering = ("-updated_at", "ticker")
