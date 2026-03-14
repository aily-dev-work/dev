from rest_framework import serializers

from .models import StockPrice5Min, StockPriceDaily, StockPriceMonthly, StockPriceWeekly, WatchStock


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


class StockPrice5MinSerializer(serializers.ModelSerializer):
    stock_ticker = serializers.ReadOnlyField(source="stock.ticker")
    stock_name = serializers.ReadOnlyField(source="stock.name")

    class Meta:
        model = StockPrice5Min
        fields = [
            "id",
            "stock",
            "stock_ticker",
            "stock_name",
            "datetime",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "stock_ticker", "stock_name")


class StockPriceWeeklySerializer(serializers.ModelSerializer):
    stock_ticker = serializers.ReadOnlyField(source="stock.ticker")
    stock_name = serializers.ReadOnlyField(source="stock.name")

    class Meta:
        model = StockPriceWeekly
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


class StockPriceMonthlySerializer(serializers.ModelSerializer):
    stock_ticker = serializers.ReadOnlyField(source="stock.ticker")
    stock_name = serializers.ReadOnlyField(source="stock.name")

    class Meta:
        model = StockPriceMonthly
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

