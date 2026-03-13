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
