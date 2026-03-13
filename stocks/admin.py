from django.contrib import admin

from .models import StockPriceDaily, WatchStock


@admin.register(WatchStock)
class WatchStockAdmin(admin.ModelAdmin):
    list_display = ("ticker", "name", "market", "is_active", "updated_at")
    list_filter = ("is_active", "market")
    search_fields = ("ticker", "name")
    ordering = ("-updated_at", "ticker")


@admin.register(StockPriceDaily)
class StockPriceDailyAdmin(admin.ModelAdmin):
    list_display = (
        "stock",
        "date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "updated_at",
    )
    list_filter = ("stock",)
    search_fields = ("stock__ticker", "stock__name")
    ordering = ("-date", "-updated_at")
