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

    # フェーズ9: このシグナルがどの ScoreProfile で生成されたかを追跡するための情報
    score_profile = models.ForeignKey(
        "ScoreProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="signals",
        help_text="このシグナル生成時に使用したスコアプロファイル",
    )
    score_profile_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="生成時点の ScoreProfile.name スナップショット",
    )
    score_profile_version = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="生成時点の ScoreProfile.version スナップショット",
    )

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


class ScoreProfile(models.Model):
    """
    買いスコア / 売りスコアの重み・閾値定義を保持するプロファイル。
    初期状態ではフェーズ4のハードコードと同じ設定を 1件だけ持つ。
    将来的に AI などから提案された設定を追加・切り替え可能にする。
    """

    name = models.CharField(max_length=100)
    version = models.CharField(
        max_length=32,
        help_text="バージョン識別子（例: 'v1', '2026-03-13-01' など）",
    )
    is_active = models.BooleanField(
        default=False,
        help_text="現在のスコア計算に利用する有効プロファイルかどうか",
    )
    description = models.TextField(
        blank=True,
        help_text="このプロファイルの用途やメモ（任意）",
    )
    weights_json = models.JSONField(
        help_text="買い/売りスコアの重み定義（例: {'buy': {...}, 'sell': {...}}）",
    )
    thresholds_json = models.JSONField(
        help_text="バイアス・強度などの閾値定義",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-updated_at"]
        verbose_name = "スコア設定プロファイル"
        verbose_name_plural = "スコア設定プロファイル"

    def __str__(self) -> str:
        return f"{self.name} ({self.version})"


class ScoreProfileProposal(models.Model):
    """
    AI による ScoreProfile レビュー結果を保存する提案モデル。
    フェーズ13では draft / reviewed / accepted / rejected の簡易ステータスのみ管理する。
    """

    STATUS_DRAFT = "draft"
    STATUS_REVIEWED = "reviewed"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "draft"),
        (STATUS_REVIEWED, "reviewed"),
        (STATUS_ACCEPTED, "accepted"),
        (STATUS_REJECTED, "rejected"),
    ]

    score_profile = models.ForeignKey(
        ScoreProfile,
        on_delete=models.CASCADE,
        related_name="proposals",
        help_text="提案の対象となる ScoreProfile",
    )
    proposal_name = models.CharField(
        max_length=255,
        help_text="人間が識別しやすい提案名（自動生成されたデフォルト名を含む）",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        help_text="提案のレビュー状態",
    )

    score_profile_name_snapshot = models.CharField(
        max_length=100,
        help_text="提案作成時点の ScoreProfile.name スナップショット",
    )
    score_profile_version_snapshot = models.CharField(
        max_length=32,
        help_text="提案作成時点の ScoreProfile.version スナップショット",
    )

    source_filters_json = models.JSONField(
        help_text="analysis-package 生成時に利用したフィルター条件（ticker, 日付範囲など）",
    )
    analysis_summary = models.TextField(
        help_text="AI による全体サマリテキスト",
    )
    issues_json = models.JSONField(
        help_text="AI が指摘した課題一覧",
    )
    improvement_hypotheses_json = models.JSONField(
        help_text="AI が提案する改善仮説一覧",
    )
    suggested_weights_json = models.JSONField(
        help_text="AI が提案する新しい weights_json",
    )
    suggested_thresholds_json = models.JSONField(
        help_text="AI が提案する新しい thresholds_json",
    )
    cautions_json = models.JSONField(
        help_text="AI が提示する注意点・リスク",
    )
    raw_ai_response_json = models.JSONField(
        help_text="AI から返却された生の JSON 応答（将来の解析用）",
    )

    review_note = models.TextField(
        blank=True,
        default="",
        help_text="人間によるレビューコメントやメモ",
    )

    applied_score_profile = models.ForeignKey(
        "ScoreProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_proposals",
        help_text="この proposal から生成された ScoreProfile（なければ NULL）",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "スコア設定プロファイル提案"
        verbose_name_plural = "スコア設定プロファイル提案"

    def __str__(self) -> str:
        return f"Proposal({self.score_profile_name_snapshot} {self.score_profile_version_snapshot} - {self.proposal_name})"


class ScoreProfileActivationHistory(models.Model):
    """
    ScoreProfile の active 切替履歴。
    「いつ」「どの profile を」「何由来で」有効化したかを追跡する。
    """

    previous_profile = models.ForeignKey(
        "ScoreProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deactivated_histories",
        help_text="切り替え前に active だった ScoreProfile（初回は NULL 可）",
    )
    activated_profile = models.ForeignKey(
        "ScoreProfile",
        on_delete=models.CASCADE,
        related_name="activated_histories",
        help_text="この履歴で active にした ScoreProfile",
    )
    source_proposal = models.ForeignKey(
        "ScoreProfileProposal",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activation_histories",
        help_text="有効化した ScoreProfile の元になった proposal（特定できる場合のみ）",
    )

    # スナップショット（FK が後で消えても追跡できるようにする）
    previous_profile_name_snapshot = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )
    previous_profile_version_snapshot = models.CharField(
        max_length=32,
        blank=True,
        default="",
    )
    activated_profile_name_snapshot = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )
    activated_profile_version_snapshot = models.CharField(
        max_length=32,
        blank=True,
        default="",
    )
    source_proposal_name_snapshot = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    activation_reason = models.CharField(
        max_length=50,
        default="manual_activate",
        help_text="active 化の理由（例: manual_activate, apply_and_activate など）",
    )
    note = models.TextField(
        blank=True,
        default="",
        help_text="任意のメモ（運用理由など）",
    )
    activated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="active 化を実行した日時",
    )

    class Meta:
        ordering = ["-activated_at", "-id"]
        verbose_name = "スコアプロファイル有効化履歴"
        verbose_name_plural = "スコアプロファイル有効化履歴"

    def __str__(self) -> str:
        return f"ActivationHistory({self.activated_profile_id} at {self.activated_at})"
