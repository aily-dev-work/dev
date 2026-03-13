from django.contrib import admin

from .models import SignalOutcome, StockPriceDaily, TradingSignal, WatchStock


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


@admin.register(TradingSignal)
class TradingSignalAdmin(admin.ModelAdmin):
    list_display = (
        "stock",
        "signal_date",
        "signal_type",
        "buy_score",
        "sell_score",
        "score_bias",
        "score_strength",
        "created_at",
    )
    list_filter = ("stock", "signal_type", "score_bias", "score_strength")
    search_fields = ("stock__ticker", "stock__name")
    ordering = ("-signal_date", "-created_at")


@admin.register(SignalOutcome)
class SignalOutcomeAdmin(admin.ModelAdmin):
    list_display = (
        "signal",
        "eval_status",
        "base_price",
        "return_5d",
        "success_5d",
        "return_10d",
        "success_10d",
        "return_20d",
        "success_20d",
        "updated_at",
    )
    list_filter = ("eval_status", "success_5d", "success_10d", "success_20d")
    search_fields = ("signal__stock__ticker", "signal__stock__name")
    ordering = ("-updated_at",)
