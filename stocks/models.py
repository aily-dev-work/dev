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


class TradingSignal(models.Model):
    """
    提案タイミングのスコアとテクニカル状態を保存するモデル。
    バックテストやAI分析の土台として利用する。
    """

    stock = models.ForeignKey(
        WatchStock,
        on_delete=models.CASCADE,
        related_name="signals",
        help_text="対象となる監視銘柄",
    )
    signal_date = models.DateField(help_text="シグナル日付（通常 latest_date）")
    signal_type = models.CharField(
        max_length=16,
        choices=(
            ("buy", "buy"),
            ("sell", "sell"),
            ("neutral", "neutral"),
        ),
    )

    buy_score = models.DecimalField(max_digits=5, decimal_places=2)
    sell_score = models.DecimalField(max_digits=5, decimal_places=2)
    score_bias = models.CharField(max_length=16)
    score_strength = models.CharField(max_length=16)

    signal_price = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="シグナル生成時の価格（通常 latest_close）",
    )

    latest_close = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    ma25 = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    ma75 = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    high_20 = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    low_20 = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )

    technical_position = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="20日レンジ内での価格位置（0〜1）",
    )

    trend_short = models.CharField(max_length=16, null=True, blank=True)
    trend_mid = models.CharField(max_length=16, null=True, blank=True)
    trend_long = models.CharField(max_length=16, null=True, blank=True)
    volume_trend = models.CharField(max_length=16, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-signal_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["stock", "signal_date"],
                name="unique_stock_signal_per_day",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.stock.ticker} {self.signal_date} {self.signal_type}"


class SignalOutcome(models.Model):
    """
    TradingSignal ごとの結果検証データ。
    5/10/20 営業日後の価格とリターン、成否を保持する。
    """

    signal = models.OneToOneField(
        TradingSignal,
        related_name="outcome",
        on_delete=models.CASCADE,
    )

    base_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    eval_status = models.CharField(max_length=16, default="pending")  # pending / partial / completed

    # 5 営業日後
    date_5d = models.DateField(null=True, blank=True)
    close_5d = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    return_5d = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    success_5d = models.BooleanField(null=True, blank=True)

    # 10 営業日後
    date_10d = models.DateField(null=True, blank=True)
    close_10d = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    return_10d = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    success_10d = models.BooleanField(null=True, blank=True)

    # 20 営業日後
    date_20d = models.DateField(null=True, blank=True)
    close_20d = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    return_20d = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    success_20d = models.BooleanField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Outcome for signal {self.signal_id}"
