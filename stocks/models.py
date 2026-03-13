from django.db import models


class WatchStock(models.Model):
    """
    監視対象の銘柄を表すモデル。
    フェーズ1では基本的な属性のみを管理する。
    """

    ticker = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="ティッカー / 銘柄コード（例: 7203.T, AAPL）",
    )
    name = models.CharField(
        max_length=255,
        help_text="銘柄名（例: トヨタ自動車, Apple Inc.）",
    )
    market = models.CharField(
        max_length=32,
        blank=True,
        help_text="市場区分（例: JP, US, TSE など。任意）",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="監視中かどうか",
    )
    memo = models.TextField(
        blank=True,
        help_text="メモ（任意）",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "ticker"]
        verbose_name = "監視銘柄"
        verbose_name_plural = "監視銘柄"

    def __str__(self) -> str:
        return f"{self.ticker} - {self.name}"


class StockPriceDaily(models.Model):
    """
    監視銘柄ごとの日足株価（OHLCV）を表すモデル。
    フェーズ2では保存と取得のみを扱う。
    """

    stock = models.ForeignKey(
        WatchStock,
        on_delete=models.CASCADE,
        related_name="daily_prices",
        help_text="対象となる監視銘柄",
    )
    date = models.DateField(help_text="日付（終値ベースの日付など）")
    open_price = models.DecimalField(max_digits=12, decimal_places=4)
    high_price = models.DecimalField(max_digits=12, decimal_places=4)
    low_price = models.DecimalField(max_digits=12, decimal_places=4)
    close_price = models.DecimalField(max_digits=12, decimal_places=4)
    volume = models.BigIntegerField(null=True, blank=True, help_text="出来高（任意）")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "日足株価"
        verbose_name_plural = "日足株価"
        ordering = ["-date", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["stock", "date"],
                name="unique_stock_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.stock.ticker} {self.date} {self.close_price}"
