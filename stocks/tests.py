from datetime import date

from django.test import TestCase

from .models import SignalOutcome, TradingSignal, WatchStock
from .services.signal_dataset import build_signal_queryset, signals_to_dataset


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
