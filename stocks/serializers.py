from rest_framework import serializers

from .models import WatchStock


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

