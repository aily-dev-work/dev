from datetime import date
from decimal import Decimal

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from .models import ScoreProfile, SignalOutcome, TradingSignal, WatchStock
from .services.analysis_package import (
    build_analysis_package_for_active_profile,
    build_analysis_package_for_profile,
)
from .services.signal_dataset import build_signal_queryset, signals_to_dataset
from .services.scoring_profile import get_active_score_profile, get_active_scoring_config
from .services.signal_generation import generate_trading_signal
from .services.signal_scoring import score_from_technical, ScoreResult
from .services.signal_summary import build_summary_queryset, summarize_signals
from .services.technical_analysis import AverageVolume, HighLow, MovingAverages, TechnicalSignals, TechnicalSummary


class SignalDatasetServiceTests(TestCase):
    def setUp(self) -> None:
        self.stock = WatchStock.objects.create(
            ticker="TEST",
            name="Test Stock",
            market="JP",
        )

        # outcome なし（未評価）signal
        self.signal_no_outcome = TradingSignal.objects.create(
            stock=self.stock,
            signal_date=date(2026, 3, 10),
            signal_type="buy",
            buy_score=10,
            sell_score=5,
            score_bias="buy",
            score_strength="weak",
            signal_price="100.0000",
            latest_close="100.0000",
            ma25="100.0000",
            ma75="100.0000",
            high_20="110.0000",
            low_20="90.0000",
            trend_short="up",
            trend_mid="up",
            trend_long="up",
        )

        # outcome.pending の signal
        self.signal_pending = TradingSignal.objects.create(
            stock=self.stock,
            signal_date=date(2026, 3, 11),
            signal_type="buy",
            buy_score=20,
            sell_score=5,
            score_bias="buy",
            score_strength="weak",
            signal_price="200.0000",
            latest_close="200.0000",
            ma25="200.0000",
            ma75="200.0000",
            high_20="210.0000",
            low_20="190.0000",
            trend_short="up",
            trend_mid="up",
            trend_long="up",
        )
        self.outcome_pending = SignalOutcome.objects.create(
            signal=self.signal_pending,
            base_price="200.0000",
            eval_status="pending",
        )

        # outcome.partial の signal
        self.signal_partial = TradingSignal.objects.create(
            stock=self.stock,
            signal_date=date(2026, 3, 12),
            signal_type="buy",
            buy_score=30,
            sell_score=5,
            score_bias="buy",
            score_strength="weak",
            signal_price="300.0000",
            latest_close="300.0000",
            ma25="300.0000",
            ma75="300.0000",
            high_20="310.0000",
            low_20="290.0000",
            trend_short="up",
            trend_mid="up",
            trend_long="up",
        )
        self.outcome_partial = SignalOutcome.objects.create(
            signal=self.signal_partial,
            base_price="300.0000",
            eval_status="partial",
        )

        # outcome.completed の signal
        self.signal_completed = TradingSignal.objects.create(
            stock=self.stock,
            signal_date=date(2026, 3, 13),
            signal_type="buy",
            buy_score=40,
            sell_score=5,
            score_bias="buy",
            score_strength="weak",
            signal_price="400.0000",
            latest_close="400.0000",
            ma25="400.0000",
            ma75="400.0000",
            high_20="410.0000",
            low_20="390.0000",
            trend_short="up",
            trend_mid="up",
            trend_long="up",
        )
        self.outcome_completed = SignalOutcome.objects.create(
            signal=self.signal_completed,
            base_price="400.0000",
            eval_status="completed",
        )

    def test_signals_to_dataset_sets_pending_for_signal_without_outcome(self) -> None:
        qs = TradingSignal.objects.select_related("stock", "outcome").all()
        dataset = signals_to_dataset(qs)

        row = next(r for r in dataset if r["signal_id"] == self.signal_no_outcome.id)
        self.assertEqual(row["eval_status"], "pending")

    def test_eval_status_pending_includes_no_outcome_and_pending(self) -> None:
        params = {"eval_status": "pending"}
        qs = build_signal_queryset(params)
        ids = list(qs.values_list("id", flat=True))

        self.assertIn(self.signal_no_outcome.id, ids)
        self.assertIn(self.signal_pending.id, ids)
        self.assertNotIn(self.signal_partial.id, ids)
        self.assertNotIn(self.signal_completed.id, ids)

    def test_eval_status_partial_and_completed_exclude_no_outcome(self) -> None:
        params_partial = {"eval_status": "partial"}
        qs_partial = build_signal_queryset(params_partial)
        ids_partial = list(qs_partial.values_list("id", flat=True))

        self.assertIn(self.signal_partial.id, ids_partial)
        self.assertNotIn(self.signal_no_outcome.id, ids_partial)
        self.assertNotIn(self.signal_pending.id, ids_partial)
        self.assertNotIn(self.signal_completed.id, ids_partial)

        params_completed = {"eval_status": "completed"}
        qs_completed = build_signal_queryset(params_completed)
        ids_completed = list(qs_completed.values_list("id", flat=True))

        self.assertIn(self.signal_completed.id, ids_completed)
        self.assertNotIn(self.signal_no_outcome.id, ids_completed)
        self.assertNotIn(self.signal_pending.id, ids_completed)
        self.assertNotIn(self.signal_partial.id, ids_completed)


class ScoreProfileServiceTests(TestCase):
    def test_get_active_score_profile_raises_when_none(self) -> None:
        ScoreProfile.objects.all().delete()
        with self.assertRaises(ImproperlyConfigured):
            get_active_score_profile()

    def test_get_active_score_profile_raises_when_multiple(self) -> None:
        ScoreProfile.objects.create(
            name="p1",
            version="v1",
            is_active=True,
            description="",
            weights_json={},
            thresholds_json={},
        )
        ScoreProfile.objects.create(
            name="p2",
            version="v2",
            is_active=True,
            description="",
            weights_json={},
            thresholds_json={},
        )

        with self.assertRaises(ImproperlyConfigured):
            get_active_score_profile()

    def test_get_active_score_profile_success(self) -> None:
        ScoreProfile.objects.all().delete()
        profile = ScoreProfile.objects.create(
            name="default",
            version="v1",
            is_active=True,
            description="",
            weights_json={"buy": {}, "sell": {}},
            thresholds_json={},
        )

        got = get_active_score_profile()
        self.assertEqual(got.id, profile.id)


class ScoreCalculationCompatibilityTests(TestCase):
    """
    旧ハードコードロジックと ScoreProfile ベースのロジックの結果が一致することをテストする。
    """

    def setUp(self) -> None:
        ScoreProfile.objects.all().delete()
        # 初期プロファイル（migration と同じ内容）
        weights = {
            "buy": {
                "trend_long_up": 20.0,
                "trend_mid_up": 15.0,
                "trend_short_up": 10.0,
                "volume_high": 10.0,
                "above_ma25": 10.0,
                "above_ma75": 10.0,
                "near_high_20": 10.0,
                "near_low_20": 10.0,
            },
            "sell": {
                "trend_long_down": 20.0,
                "trend_mid_down": 15.0,
                "trend_short_down": 10.0,
                "volume_low": 10.0,
                "below_ma25": 10.0,
                "below_ma75": 10.0,
                "near_low_20": 10.0,
                "near_high_20": 10.0,
            },
        }
        thresholds = {
            "bias": {
                "neutral_abs_diff_lt": 10.0,
            },
            "strength": {
                "weak_abs_diff_lt": 15.0,
                "normal_abs_diff_lt": 30.0,
            },
        }
        ScoreProfile.objects.create(
            name="Default scoring profile",
            version="v1",
            is_active=True,
            description="",
            weights_json=weights,
            thresholds_json=thresholds,
        )

    def _old_logic_score(self, summary: TechnicalSummary) -> ScoreResult:
        """
        旧 signal_scoring.py のロジックをテスト内に再現し、期待値を計算する。
        """
        BUY_WEIGHTS = {
            "trend_long_up": 20.0,
            "trend_mid_up": 15.0,
            "trend_short_up": 10.0,
            "volume_high": 10.0,
            "above_ma25": 10.0,
            "above_ma75": 10.0,
            "near_high_20": 10.0,
            "near_low_20": 10.0,
        }
        SELL_WEIGHTS = {
            "trend_long_down": 20.0,
            "trend_mid_down": 15.0,
            "trend_short_down": 10.0,
            "volume_low": 10.0,
            "below_ma25": 10.0,
            "below_ma75": 10.0,
            "near_low_20": 10.0,
            "near_high_20": 10.0,
        }

        def clamp(score: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
            return max(min(score, max_value), min_value)

        breakdown_buy: dict[str, float] = {}
        breakdown_sell: dict[str, float] = {}
        insufficient_reasons: list[str] = []

        signals = summary.signals
        ma = summary.moving_averages
        hl = summary.high_low
        latest_close: Optional[Decimal] = summary.latest_close

        # トレンド系
        if signals.trend_long == "up":
            breakdown_buy["trend_long_up"] = BUY_WEIGHTS["trend_long_up"]
        else:
            breakdown_buy["trend_long_up"] = 0.0
        if signals.trend_long == "down":
            breakdown_sell["trend_long_down"] = SELL_WEIGHTS["trend_long_down"]
        else:
            breakdown_sell["trend_long_down"] = 0.0

        if signals.trend_mid == "up":
            breakdown_buy["trend_mid_up"] = BUY_WEIGHTS["trend_mid_up"]
        else:
            breakdown_buy["trend_mid_up"] = 0.0
        if signals.trend_mid == "down":
            breakdown_sell["trend_mid_down"] = SELL_WEIGHTS["trend_mid_down"]
        else:
            breakdown_sell["trend_mid_down"] = 0.0

        if signals.trend_short == "up":
            breakdown_buy["trend_short_up"] = BUY_WEIGHTS["trend_short_up"]
        else:
            breakdown_buy["trend_short_up"] = 0.0
        if signals.trend_short == "down":
            breakdown_sell["trend_short_down"] = SELL_WEIGHTS["trend_short_down"]
        else:
            breakdown_sell["trend_short_down"] = 0.0

        # 出来高
        if signals.volume_trend == "high":
            breakdown_buy["volume_high"] = BUY_WEIGHTS["volume_high"]
        else:
            breakdown_buy["volume_high"] = 0.0

        if signals.volume_trend == "low":
            breakdown_sell["volume_low"] = SELL_WEIGHTS["volume_low"]
        else:
            breakdown_sell["volume_low"] = 0.0

        if signals.volume_trend is None:
            insufficient_reasons.append("volume_trend_missing")

        # ma25
        if latest_close is not None and ma.ma25 is not None:
            if latest_close > ma.ma25:
                breakdown_buy["above_ma25"] = BUY_WEIGHTS["above_ma25"]
                breakdown_sell["below_ma25"] = 0.0
            elif latest_close < ma.ma25:
                breakdown_sell["below_ma25"] = SELL_WEIGHTS["below_ma25"]
                breakdown_buy["above_ma25"] = 0.0
            else:
                breakdown_buy["above_ma25"] = 0.0
                breakdown_sell["below_ma25"] = 0.0
        else:
            breakdown_buy["above_ma25"] = 0.0
            breakdown_sell["below_ma25"] = 0.0
            insufficient_reasons.append("ma25_or_latest_missing")

        # ma75
        if latest_close is not None and ma.ma75 is not None:
            if latest_close > ma.ma75:
                breakdown_buy["above_ma75"] = BUY_WEIGHTS["above_ma75"]
                breakdown_sell["below_ma75"] = 0.0
            elif latest_close < ma.ma75:
                breakdown_sell["below_ma75"] = SELL_WEIGHTS["below_ma75"]
                breakdown_buy["above_ma75"] = 0.0
            else:
                breakdown_buy["above_ma75"] = 0.0
                breakdown_sell["below_ma75"] = 0.0
        else:
            breakdown_buy["above_ma75"] = 0.0
            breakdown_sell["below_ma75"] = 0.0
            insufficient_reasons.append("ma75_or_latest_missing")

        # high_20 / low_20
        if latest_close is not None and hl.high_20 is not None and hl.low_20 is not None:
            price_range = hl.high_20 - hl.low_20
            if price_range > 0:
                pos = float((latest_close - hl.low_20) / price_range)
                if pos >= 0.8:
                    breakdown_sell["near_high_20"] = SELL_WEIGHTS["near_high_20"]
                else:
                    breakdown_sell["near_high_20"] = 0.0
                if pos <= 0.2:
                    breakdown_buy["near_low_20"] = BUY_WEIGHTS["near_low_20"]
                else:
                    breakdown_buy["near_low_20"] = 0.0
            else:
                breakdown_buy["near_low_20"] = 0.0
                breakdown_sell["near_high_20"] = 0.0
                insufficient_reasons.append("high_low_range_zero")
        else:
            breakdown_buy["near_low_20"] = 0.0
            breakdown_sell["near_high_20"] = 0.0
            insufficient_reasons.append("high_20_or_low_20_or_latest_missing")

        raw_buy = sum(breakdown_buy.values())
        raw_sell = sum(breakdown_sell.values())

        buy_score = clamp(raw_buy)
        sell_score = clamp(raw_sell)

        diff = buy_score - sell_score
        abs_diff = abs(diff)

        if abs_diff < 10:
            bias = "neutral"
        elif diff >= 10:
            bias = "buy"
        else:
            bias = "sell"

        if abs_diff < 15:
            strength = "weak"
        elif abs_diff < 30:
            strength = "normal"
        else:
            strength = "strong"

        insufficient_data = len(insufficient_reasons) > 0
        reason_text = ", ".join(sorted(set(insufficient_reasons))) if insufficient_reasons else None

        return ScoreResult(
            buy_score=buy_score,
            sell_score=sell_score,
            breakdown_buy=breakdown_buy,
            breakdown_sell=breakdown_sell,
            insufficient_data=insufficient_data,
            insufficient_reason=reason_text,
            bias=bias,
            strength=strength,
        )

    def test_score_from_technical_compatible_with_old_logic(self) -> None:
        """
        代表的な1ケースで、新ロジックと旧ロジックの結果が完全一致することを確認する。
        """
        stock = WatchStock.objects.create(ticker="COMP", name="Compat", market="JP")
        summary = TechnicalSummary(
            stock=stock,
            latest_date="2026-03-13",
            latest_close=Decimal("2520.0000"),
            moving_averages=MovingAverages(
                ma5=Decimal("2500.0000"),
                ma25=Decimal("2480.0000"),
                ma75=Decimal("2400.0000"),
            ),
            high_low=HighLow(
                high_20=Decimal("2550.0000"),
                low_20=Decimal("2400.0000"),
            ),
            average_volume=AverageVolume(
                avg_volume_5=1000000.0,
                avg_volume_20=800000.0,
            ),
            signals=TechnicalSignals(
                trend_short="up",
                trend_mid="up",
                trend_long="up",
                volume_trend="normal",
            ),
        )

        expected = self._old_logic_score(summary)
        actual = score_from_technical(summary)

        self.assertEqual(expected.buy_score, actual.buy_score)
        self.assertEqual(expected.sell_score, actual.sell_score)
        self.assertEqual(expected.bias, actual.bias)
        self.assertEqual(expected.strength, actual.strength)
        self.assertEqual(expected.breakdown_buy, actual.breakdown_buy)
        self.assertEqual(expected.breakdown_sell, actual.breakdown_sell)


class TradingSignalScoreProfileTests(TestCase):
    """
    フェーズ9: TradingSignal に ScoreProfile 情報が保存されることを確認するテスト。
    """

    def setUp(self) -> None:
        ScoreProfile.objects.all().delete()
        self.profile = ScoreProfile.objects.create(
            name="Phase9 profile",
            version="v1",
            is_active=True,
            description="for tests",
            weights_json={
                "buy": {
                    "trend_long_up": 20.0,
                    "trend_mid_up": 15.0,
                    "trend_short_up": 10.0,
                },
                "sell": {
                    "trend_long_down": 20.0,
                    "trend_mid_down": 15.0,
                    "trend_short_down": 10.0,
                },
            },
            thresholds_json={
                "bias": {"neutral_abs_diff_lt": 10.0},
                "strength": {"weak_abs_diff_lt": 15.0, "normal_abs_diff_lt": 30.0},
            },
        )

    def test_generate_trading_signal_saves_score_profile_info(self) -> None:
        stock = WatchStock.objects.create(ticker="P9", name="Phase9", market="JP")
        summary = TechnicalSummary(
            stock=stock,
            latest_date="2026-03-13",
            latest_close=Decimal("100.0000"),
            moving_averages=MovingAverages(
                ma5=Decimal("100.0000"),
                ma25=Decimal("100.0000"),
                ma75=Decimal("100.0000"),
            ),
            high_low=HighLow(
                high_20=Decimal("110.0000"),
                low_20=Decimal("90.0000"),
            ),
            average_volume=AverageVolume(
                avg_volume_5=1000.0,
                avg_volume_20=1000.0,
            ),
            signals=TechnicalSignals(
                trend_short="flat",
                trend_mid="flat",
                trend_long="flat",
                volume_trend="normal",
            ),
        )

        score = score_from_technical(summary)
        signal = generate_trading_signal(stock, summary, score)

        self.assertEqual(signal.score_profile_id, self.profile.id)
        self.assertEqual(signal.score_profile_name, self.profile.name)
        self.assertEqual(signal.score_profile_version, self.profile.version)

    def test_dataset_contains_score_profile_fields(self) -> None:
        stock = WatchStock.objects.create(ticker="P9D", name="Phase9D", market="JP")
        summary = TechnicalSummary(
            stock=stock,
            latest_date="2026-03-14",
            latest_close=Decimal("200.0000"),
            moving_averages=MovingAverages(
                ma5=Decimal("190.0000"),
                ma25=Decimal("180.0000"),
                ma75=Decimal("170.0000"),
            ),
            high_low=HighLow(
                high_20=Decimal("210.0000"),
                low_20=Decimal("190.0000"),
            ),
            average_volume=AverageVolume(
                avg_volume_5=2000.0,
                avg_volume_20=2000.0,
            ),
            signals=TechnicalSignals(
                trend_short="up",
                trend_mid="up",
                trend_long="up",
                volume_trend="high",
            ),
        )

        score = score_from_technical(summary)
        signal = generate_trading_signal(stock, summary, score)

        qs = build_signal_queryset({})
        rows = signals_to_dataset(qs)
        row = next(r for r in rows if r["signal_id"] == signal.id)

        self.assertEqual(row["score_profile_id"], self.profile.id)
        self.assertEqual(row["score_profile_name"], self.profile.name)
        self.assertEqual(row["score_profile_version"], self.profile.version)

    def test_score_profile_set_null_keeps_snapshot_fields(self) -> None:
        stock = WatchStock.objects.create(ticker="P9N", name="Phase9N", market="JP")
        summary = TechnicalSummary(
            stock=stock,
            latest_date="2026-03-15",
            latest_close=Decimal("300.0000"),
            moving_averages=MovingAverages(
                ma5=Decimal("290.0000"),
                ma25=Decimal("280.0000"),
                ma75=Decimal("270.0000"),
            ),
            high_low=HighLow(
                high_20=Decimal("310.0000"),
                low_20=Decimal("290.0000"),
            ),
            average_volume=AverageVolume(
                avg_volume_5=3000.0,
                avg_volume_20=3000.0,
            ),
            signals=TechnicalSignals(
                trend_short="up",
                trend_mid="up",
                trend_long="up",
                volume_trend="normal",
            ),
        )

        score = score_from_technical(summary)
        signal = generate_trading_signal(stock, summary, score)

        # プロファイルを削除（FK は SET_NULL）
        self.profile.delete()
        signal.refresh_from_db()

        self.assertIsNone(signal.score_profile)
        # name/version のスナップショットは残る
        self.assertEqual(signal.score_profile_name, "Phase9 profile")
        self.assertEqual(signal.score_profile_version, "v1")


class SignalSummaryTests(TestCase):
    """
    フェーズ10: ScoreProfile / signal_type 単位の集計 summary をテストする。
    """

    def setUp(self) -> None:
        ScoreProfile.objects.all().delete()
        # 2つのプロファイル (A, B)
        self.profile_a = ScoreProfile.objects.create(
            name="ProfileA",
            version="v1",
            is_active=True,
            description="",
            weights_json={"buy": {}, "sell": {}},
            thresholds_json={},
        )
        self.profile_b = ScoreProfile.objects.create(
            name="ProfileB",
            version="v1",
            is_active=False,
            description="",
            weights_json={"buy": {}, "sell": {}},
            thresholds_json={},
        )

        self.stock = WatchStock.objects.create(ticker="SUMM", name="SummaryStock", market="JP")

        # ProfileA, buy, 成功/失敗入り混じり
        self.sig_a1 = TradingSignal.objects.create(
            stock=self.stock,
            signal_date=date(2026, 3, 1),
            signal_type="buy",
            buy_score=10,
            sell_score=5,
            score_bias="buy",
            score_strength="weak",
            signal_price="100.0000",
            latest_close="100.0000",
            ma25="100.0000",
            ma75="100.0000",
            high_20="110.0000",
            low_20="90.0000",
            score_profile=self.profile_a,
            score_profile_name=self.profile_a.name,
            score_profile_version=self.profile_a.version,
        )
        SignalOutcome.objects.create(
            signal=self.sig_a1,
            base_price="100.0000",
            return_5d=Decimal("0.10"),  # +10%
            success_5d=True,
            return_10d=Decimal("-0.05"),  # -5%
            success_10d=False,
            return_20d=None,
            success_20d=None,
        )

        self.sig_a2 = TradingSignal.objects.create(
            stock=self.stock,
            signal_date=date(2026, 3, 2),
            signal_type="buy",
            buy_score=20,
            sell_score=5,
            score_bias="buy",
            score_strength="weak",
            signal_price="200.0000",
            latest_close="200.0000",
            ma25="200.0000",
            ma75="200.0000",
            high_20="210.0000",
            low_20="190.0000",
            score_profile=self.profile_a,
            score_profile_name=self.profile_a.name,
            score_profile_version=self.profile_a.version,
        )
        SignalOutcome.objects.create(
            signal=self.sig_a2,
            base_price="200.0000",
            return_5d=Decimal("0.00"),  # 0%
            success_5d=False,
            return_10d=None,
            success_10d=None,
            return_20d=Decimal("0.20"),  # +20%
            success_20d=True,
        )

        # ProfileB, sell
        self.sig_b1 = TradingSignal.objects.create(
            stock=self.stock,
            signal_date=date(2026, 3, 3),
            signal_type="sell",
            buy_score=5,
            sell_score=15,
            score_bias="sell",
            score_strength="weak",
            signal_price="300.0000",
            latest_close="300.0000",
            ma25="300.0000",
            ma75="300.0000",
            high_20="310.0000",
            low_20="290.0000",
            score_profile=self.profile_b,
            score_profile_name=self.profile_b.name,
            score_profile_version=self.profile_b.version,
        )
        SignalOutcome.objects.create(
            signal=self.sig_b1,
            base_price="300.0000",
            return_5d=Decimal("-0.10"),  # -10%
            success_5d=True,  # sell なので下落で成功
            return_10d=None,
            success_10d=None,
            return_20d=None,
            success_20d=None,
        )

        # outcome 未評価のシグナル (ProfileA, buy)
        self.sig_a3 = TradingSignal.objects.create(
            stock=self.stock,
            signal_date=date(2026, 3, 4),
            signal_type="buy",
            buy_score=30,
            sell_score=5,
            score_bias="buy",
            score_strength="weak",
            signal_price="400.0000",
            latest_close="400.0000",
            ma25="400.0000",
            ma75="400.0000",
            high_20="410.0000",
            low_20="390.0000",
            score_profile=self.profile_a,
            score_profile_name=self.profile_a.name,
            score_profile_version=self.profile_a.version,
        )

    def test_summary_groups_by_profile_and_signal_type(self) -> None:
        qs = build_summary_queryset({})
        rows = summarize_signals(qs)

        # ProfileA, buy
        row_a_buy = next(
            r
            for r in rows
            if r["score_profile_name"] == "ProfileA"
            and r["score_profile_version"] == "v1"
            and r["signal_type"] == "buy"
        )
        self.assertEqual(row_a_buy["total_signals"], 3)

        # ProfileB, sell
        row_b_sell = next(
            r
            for r in rows
            if r["score_profile_name"] == "ProfileB"
            and r["score_profile_version"] == "v1"
            and r["signal_type"] == "sell"
        )
        self.assertEqual(row_b_sell["total_signals"], 1)

    def test_success_rate_and_avg_return_are_computed_correctly(self) -> None:
        qs = build_summary_queryset({})
        rows = summarize_signals(qs)

        row_a_buy = next(
            r
            for r in rows
            if r["score_profile_name"] == "ProfileA"
            and r["score_profile_version"] == "v1"
            and r["signal_type"] == "buy"
        )

        # 5d: sig_a1(+0.10, success=True), sig_a2(0.00, success=False), sig_a3(未評価)
        h5 = row_a_buy["h5"]
        self.assertEqual(h5["evaluated_count"], 2)
        self.assertEqual(h5["success_count"], 1)
        self.assertAlmostEqual(h5["success_rate"], 0.5)
        self.assertAlmostEqual(h5["avg_return"], float((Decimal("0.10") + Decimal("0.00")) / 2))

        # 10d: sig_a1(-0.05, success=False), sig_a2(None), sig_a3(None)
        h10 = row_a_buy["h10"]
        self.assertEqual(h10["evaluated_count"], 1)
        self.assertEqual(h10["success_count"], 0)
        self.assertAlmostEqual(h10["success_rate"], 0.0)
        self.assertAlmostEqual(h10["avg_return"], float(Decimal("-0.05")))

        # 20d: sig_a1(None), sig_a2(+0.20, success=True), sig_a3(None)
        h20 = row_a_buy["h20"]
        self.assertEqual(h20["evaluated_count"], 1)
        self.assertEqual(h20["success_count"], 1)
        self.assertAlmostEqual(h20["success_rate"], 1.0)
        self.assertAlmostEqual(h20["avg_return"], float(Decimal("0.20")))

    def test_un_evaluated_signals_are_not_counted_as_evaluated(self) -> None:
        qs = build_summary_queryset({})
        rows = summarize_signals(qs)

        row_b_sell = next(
            r
            for r in rows
            if r["score_profile_name"] == "ProfileB"
            and r["signal_type"] == "sell"
        )

        # ProfileB の sell シグナルは1件だけ、5d は1件評価済み
        h5 = row_b_sell["h5"]
        self.assertEqual(h5["evaluated_count"], 1)
        self.assertEqual(h5["success_count"], 1)
        self.assertAlmostEqual(h5["success_rate"], 1.0)

        # 10d/20d は未評価なので evaluated_count=0
        self.assertEqual(row_b_sell["h10"]["evaluated_count"], 0)
        self.assertIsNone(row_b_sell["h10"]["success_rate"])
        self.assertIsNone(row_b_sell["h10"]["avg_return"])

        self.assertEqual(row_b_sell["h20"]["evaluated_count"], 0)
        self.assertIsNone(row_b_sell["h20"]["success_rate"])
        self.assertIsNone(row_b_sell["h20"]["avg_return"])

    def test_filters_work(self) -> None:
        # score_profile_name で絞り込み
        params = {"score_profile_name": "ProfileA"}
        qs = build_summary_queryset(params)
        rows = summarize_signals(qs)
        self.assertTrue(all(r["score_profile_name"] == "ProfileA" for r in rows))

        # signal_type で絞り込み
        params = {"signal_type": "sell"}
        qs = build_summary_queryset(params)
        rows = summarize_signals(qs)
        self.assertTrue(all(r["signal_type"] == "sell" for r in rows))


class AnalysisPackageTests(TestCase):
    """
    フェーズ11: analysis-package 用 service のテスト。
    """

    def setUp(self) -> None:
        ScoreProfile.objects.all().delete()
        self.profile = ScoreProfile.objects.create(
            name="AnalysisProfile",
            version="v1",
            is_active=True,
            description="for analysis package tests",
            weights_json={"buy": {"trend_long_up": 10.0}, "sell": {}},
            thresholds_json={"bias": {"neutral_abs_diff_lt": 10.0}, "strength": {}},
        )

        self.stock = WatchStock.objects.create(ticker="ANL", name="AnalysisStock", market="JP")

        # 3件のシグナル（うち2件だけを analysis package 対象に含めるため、フィルタで絞り込む）
        self.sig1 = TradingSignal.objects.create(
            stock=self.stock,
            signal_date=date(2026, 3, 10),
            signal_type="buy",
            buy_score=10,
            sell_score=5,
            score_bias="buy",
            score_strength="weak",
            signal_price="100.0000",
            latest_close="100.0000",
            ma25="100.0000",
            ma75="100.0000",
            high_20="110.0000",
            low_20="90.0000",
            score_profile=self.profile,
            score_profile_name=self.profile.name,
            score_profile_version=self.profile.version,
        )
        SignalOutcome.objects.create(
            signal=self.sig1,
            base_price="100.0000",
            return_5d=Decimal("0.10"),
            success_5d=True,
        )

        self.sig2 = TradingSignal.objects.create(
            stock=self.stock,
            signal_date=date(2026, 3, 11),
            signal_type="buy",
            buy_score=20,
            sell_score=5,
            score_bias="buy",
            score_strength="weak",
            signal_price="110.0000",
            latest_close="110.0000",
            ma25="105.0000",
            ma75="100.0000",
            high_20="120.0000",
            low_20="100.0000",
            score_profile=self.profile,
            score_profile_name=self.profile.name,
            score_profile_version=self.profile.version,
        )
        SignalOutcome.objects.create(
            signal=self.sig2,
            base_price="110.0000",
            return_5d=Decimal("0.00"),
            success_5d=False,
        )

        # 別 ticker（フィルタで除外されることを確認）
        other_stock = WatchStock.objects.create(ticker="OTHER", name="Other", market="JP")
        self.sig_other = TradingSignal.objects.create(
            stock=other_stock,
            signal_date=date(2026, 3, 12),
            signal_type="buy",
            buy_score=30,
            sell_score=5,
            score_bias="buy",
            score_strength="weak",
            signal_price="200.0000",
            latest_close="200.0000",
            score_profile=self.profile,
            score_profile_name=self.profile.name,
            score_profile_version=self.profile.version,
        )

    def test_build_analysis_package_for_profile_basic_structure(self) -> None:
        params = {"ticker": "ANL", "limit": "10"}
        package = build_analysis_package_for_profile(self.profile, params)

        # target_profile
        tp = package["target_profile"]
        self.assertEqual(tp["id"], self.profile.id)
        self.assertEqual(tp["name"], self.profile.name)
        self.assertEqual(tp["version"], self.profile.version)
        self.assertTrue("is_active" in tp)

        # config
        cfg = package["config"]
        self.assertEqual(cfg["weights_json"], self.profile.weights_json)
        self.assertEqual(cfg["thresholds_json"], self.profile.thresholds_json)

        # filters
        flt = package["filters"]
        self.assertEqual(flt["ticker"], "ANL")
        self.assertEqual(flt["limit"], 10)

        # dataset_rows: ticker=ANL の2件のみ
        rows = package["dataset_rows"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["ticker"] == "ANL" for r in rows))

        # summary も同じフィルタ条件で profile/name/version 単位に集計されている
        summary = package["summary"]
        self.assertTrue(len(summary) >= 1)
        self.assertTrue(
            all(
                r["score_profile_name"] == self.profile.name
                and r["score_profile_version"] == self.profile.version
                for r in summary
            )
        )

        # notes が固定文として入っている
        self.assertIn("This package is intended as input for AI-based analysis", package["notes"])

    def test_limit_is_applied(self) -> None:
        params = {"ticker": "ANL", "limit": "1"}
        package = build_analysis_package_for_profile(self.profile, params)
        rows = package["dataset_rows"]
        self.assertEqual(len(rows), 1)

    def test_active_profile_helper_uses_active_profile(self) -> None:
        params = {"ticker": "ANL"}
        package = build_analysis_package_for_active_profile(params)
        tp = package["target_profile"]
        self.assertEqual(tp["id"], self.profile.id)
