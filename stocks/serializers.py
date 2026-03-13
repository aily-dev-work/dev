from rest_framework import serializers

from .models import StockPriceDaily, WatchStock


class WatchStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchStock
        fields = [
            "id",
            "ticker",
            "name",
            "market",
            "is_active",
            "memo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class StockPriceDailySerializer(serializers.ModelSerializer):
    stock_ticker = serializers.ReadOnlyField(source="stock.ticker")
    stock_name = serializers.ReadOnlyField(source="stock.name")

    class Meta:
        model = StockPriceDaily
        fields = [
            "id",
            "stock",
            "stock_ticker",
            "stock_name",
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "stock_ticker", "stock_name")

