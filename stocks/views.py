from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from datetime import date

from .models import (
    ScoreProfile,
    ScoreProfileActivationHistory,
    ScoreProfileProposal,
    SignalOutcome,
    StockPriceDaily,
    TradingSignal,
    WatchStock,
)
from .serializers import StockPriceDailySerializer, WatchStockSerializer
from .services.signal_dataset import build_signal_queryset, signals_to_dataset
from .services.analysis_package import (
    build_analysis_package_for_active_profile,
    build_analysis_package_for_profile,
)
from .services.ai_profile_review import (
    build_ai_review_for_active_profile,
    build_ai_review_for_profile,
)
from .services.signal_summary import build_summary_queryset, summarize_signals
from .services.scoring_profile import get_active_score_profile
from .services.signal_evaluation import evaluate_signal
from .services.signal_generation import generate_trading_signal
from .services.signal_scoring import score_from_technical
from .services.technical_analysis import calculate_technical_summary
from .services.profile_proposal import save_profile_proposal
from .services.profile_proposal_review import (
    can_delete,
    update_review_fields,
    validate_status,
)
from .services.profile_apply import apply_proposal_to_new_profile
from .services.profile_activation import activate_score_profile
from .services.profile_rollback import RollbackNotAllowedError, rollback_to_previous_profile
from .services.profile_review_targets import (
    DEFAULT_MIN_EVALUATED_COUNT,
    DEFAULT_STALE_DAYS,
    DEFAULT_THRESHOLD_SUCCESS_RATE,
    get_review_targets,
)
from .services.profile_comparison import compare_profiles
from .services.profile_ops_summary import build_ops_summary


class WatchStockViewSet(viewsets.ModelViewSet):
    """
    WatchStock の CRUD を行う ViewSet。
    フェーズ1では認証・権限制御は行わず、最小構成とする。
    """

    queryset = WatchStock.objects.all()
    serializer_class = WatchStockSerializer

    @action(detail=True, methods=["get"], url_path="technical")
    def technical(self, request, pk=None):
        """
        1銘柄分のテクニカルサマリを返す。
        """
        stock = self.get_object()
        summary = calculate_technical_summary(stock)

        data = {
            "stock_id": stock.id,
            "ticker": stock.ticker,
            "name": stock.name,
            "latest_date": summary.latest_date,
            "latest_close": str(summary.latest_close) if summary.latest_close is not None else None,
            "moving_averages": {
                "ma5": str(summary.moving_averages.ma5) if summary.moving_averages.ma5 is not None else None,
                "ma25": str(summary.moving_averages.ma25) if summary.moving_averages.ma25 is not None else None,
                "ma75": str(summary.moving_averages.ma75) if summary.moving_averages.ma75 is not None else None,
            },
            "high_low": {
                "high_20": str(summary.high_low.high_20) if summary.high_low.high_20 is not None else None,
                "low_20": str(summary.high_low.low_20) if summary.high_low.low_20 is not None else None,
            },
            "average_volume": {
                "avg_volume_5": summary.average_volume.avg_volume_5,
                "avg_volume_20": summary.average_volume.avg_volume_20,
            },
            "signals": {
                "trend_short": summary.signals.trend_short,
                "trend_mid": summary.signals.trend_mid,
                "trend_long": summary.signals.trend_long,
                "volume_trend": summary.signals.volume_trend,
            },
        }

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="score")
    def score(self, request, pk=None):
        """
        1銘柄分の買い/売りスコアを返す。
        """
        stock = self.get_object()
        summary = calculate_technical_summary(stock)
        score_result = score_from_technical(summary)

        response_data = {
            "stock_id": stock.id,
            "ticker": stock.ticker,
            "name": stock.name,
            "buy_score": score_result.buy_score,
            "sell_score": score_result.sell_score,
            "score_bias": score_result.bias,
            "score_strength": score_result.strength,
            "score_breakdown": {
                "buy": score_result.breakdown_buy,
                "sell": score_result.breakdown_sell,
            },
            "technical_summary": {
                "latest_date": summary.latest_date,
                "latest_close": str(summary.latest_close) if summary.latest_close is not None else None,
                "moving_averages": {
                    "ma25": str(summary.moving_averages.ma25) if summary.moving_averages.ma25 is not None else None,
                    "ma75": str(summary.moving_averages.ma75) if summary.moving_averages.ma75 is not None else None,
                },
                "high_low": {
                    "high_20": str(summary.high_low.high_20) if summary.high_low.high_20 is not None else None,
                    "low_20": str(summary.high_low.low_20) if summary.high_low.low_20 is not None else None,
                },
                "signals": {
                    "trend_short": summary.signals.trend_short,
                    "trend_mid": summary.signals.trend_mid,
                    "trend_long": summary.signals.trend_long,
                    "volume_trend": summary.signals.volume_trend,
                },
            },
            "insufficient_data": score_result.insufficient_data,
            "insufficient_reason": score_result.insufficient_reason,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="generate-signal")
    def generate_signal(self, request, pk=None):
        """
        1銘柄分のテクニカルサマリとスコアから TradingSignal を生成・保存する。
        """
        stock = self.get_object()
        summary = calculate_technical_summary(stock)
        score_result = score_from_technical(summary)
        signal = generate_trading_signal(stock, summary, score_result)

        data = {
            "id": signal.id,
            "stock_id": stock.id,
            "signal_date": signal.signal_date.isoformat(),
            "signal_type": signal.signal_type,
            "buy_score": float(signal.buy_score),
            "sell_score": float(signal.sell_score),
            "score_bias": signal.score_bias,
            "score_strength": signal.score_strength,
            "signal_price": str(signal.signal_price) if signal.signal_price is not None else None,
            "latest_close": str(signal.latest_close) if signal.latest_close is not None else None,
            "ma25": str(signal.ma25) if signal.ma25 is not None else None,
            "ma75": str(signal.ma75) if signal.ma75 is not None else None,
            "high_20": str(signal.high_20) if signal.high_20 is not None else None,
            "low_20": str(signal.low_20) if signal.low_20 is not None else None,
            "trend_short": signal.trend_short,
            "trend_mid": signal.trend_mid,
            "trend_long": signal.trend_long,
            "volume_trend": signal.volume_trend,
            "created_at": signal.created_at.isoformat(),
        }

        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="signals")
    def signals(self, request, pk=None):
        """
        指定銘柄の TradingSignal 履歴を返す。
        """
        stock = self.get_object()
        qs = TradingSignal.objects.filter(stock=stock).order_by("-signal_date", "-created_at")

        results = []
        for s in qs:
            results.append(
                {
                    "id": s.id,
                    "stock_id": s.stock_id,
                    "signal_date": s.signal_date.isoformat(),
                    "signal_type": s.signal_type,
                    "buy_score": float(s.buy_score),
                    "sell_score": float(s.sell_score),
                    "score_bias": s.score_bias,
                    "score_strength": s.score_strength,
                    "signal_price": str(s.signal_price) if s.signal_price is not None else None,
                    "score_profile_id": s.score_profile_id,
                    "score_profile_name": s.score_profile_name,
                    "score_profile_version": s.score_profile_version,
                    "created_at": s.created_at.isoformat(),
                }
            )

        return Response(results, status=status.HTTP_200_OK)


class StockPriceDailyViewSet(viewsets.ModelViewSet):
    """
    StockPriceDaily の CRUD を行う ViewSet。
    フェーズ2では、シンプルなフィルタ機能のみ提供する。
    """

    serializer_class = StockPriceDailySerializer

    def get_queryset(self):
        """
        ?stock=<id> または ?ticker=<ticker> で絞り込み可能。
        いずれも無指定の場合は全件（新しい日付順）。
        """
        qs = StockPriceDaily.objects.select_related("stock").all()

        stock_id = self.request.query_params.get("stock")
        ticker = self.request.query_params.get("ticker")

        if stock_id:
            qs = qs.filter(stock_id=stock_id)
        if ticker:
            qs = qs.filter(stock__ticker=ticker)

        return qs


class SignalViewSet(viewsets.ViewSet):
    """
    TradingSignal 単位の評価 / 結果取得 / データセット取得用 ViewSet。
    """

    def _get_signal(self, pk: str) -> TradingSignal:
        return TradingSignal.objects.select_related("stock").get(pk=pk)

    @action(detail=True, methods=["post"], url_path="evaluate")
    def evaluate(self, request, pk=None):
        """
        指定 TradingSignal を評価して SignalOutcome を保存する。
        """
        signal = self._get_signal(pk)
        outcome = evaluate_signal(signal)

        data = {
            "signal_id": signal.id,
            "stock_id": signal.stock.id,
            "ticker": signal.stock.ticker,
            "signal_type": signal.signal_type,
            "signal_date": signal.signal_date.isoformat(),
            "base_price": str(outcome.base_price) if outcome.base_price is not None else None,
            "eval_status": outcome.eval_status,
            "outcomes": {
                "5d": {
                    "date": outcome.date_5d.isoformat() if outcome.date_5d else None,
                    "close": str(outcome.close_5d) if outcome.close_5d is not None else None,
                    "return": str(outcome.return_5d) if outcome.return_5d is not None else None,
                    "success": outcome.success_5d,
                },
                "10d": {
                    "date": outcome.date_10d.isoformat() if outcome.date_10d else None,
                    "close": str(outcome.close_10d) if outcome.close_10d is not None else None,
                    "return": str(outcome.return_10d) if outcome.return_10d is not None else None,
                    "success": outcome.success_10d,
                },
                "20d": {
                    "date": outcome.date_20d.isoformat() if outcome.date_20d else None,
                    "close": str(outcome.close_20d) if outcome.close_20d is not None else None,
                    "return": str(outcome.return_20d) if outcome.return_20d is not None else None,
                    "success": outcome.success_20d,
                },
            },
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="outcome")
    def outcome(self, request, pk=None):
        """
        指定 TradingSignal の Outcome を返す。
        未評価の場合は 404 を返す。
        """
        signal = self._get_signal(pk)
        try:
            outcome = signal.outcome
        except SignalOutcome.DoesNotExist:
            return Response(
                {"detail": "Outcome not evaluated yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = {
            "signal_id": signal.id,
            "stock_id": signal.stock.id,
            "ticker": signal.stock.ticker,
            "signal_type": signal.signal_type,
            "signal_date": signal.signal_date.isoformat(),
            "base_price": str(outcome.base_price) if outcome.base_price is not None else None,
            "eval_status": outcome.eval_status,
            "outcomes": {
                "5d": {
                    "date": outcome.date_5d.isoformat() if outcome.date_5d else None,
                    "close": str(outcome.close_5d) if outcome.close_5d is not None else None,
                    "return": str(outcome.return_5d) if outcome.return_5d is not None else None,
                    "success": outcome.success_5d,
                },
                "10d": {
                    "date": outcome.date_10d.isoformat() if outcome.date_10d else None,
                    "close": str(outcome.close_10d) if outcome.close_10d is not None else None,
                    "return": str(outcome.return_10d) if outcome.return_10d is not None else None,
                    "success": outcome.success_10d,
                },
                "20d": {
                    "date": outcome.date_20d.isoformat() if outcome.date_20d else None,
                    "close": str(outcome.close_20d) if outcome.close_20d is not None else None,
                    "return": str(outcome.return_20d) if outcome.return_20d is not None else None,
                    "success": outcome.success_20d,
                },
            },
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="dataset")
    def dataset(self, request):
        """
        TradingSignal + SignalOutcome を結合したフラットな一覧を返す。
        AI 入力や検証用の 1シグナル=1行データセット。
        """
        qs = build_signal_queryset(request.query_params)
        rows = signals_to_dataset(qs)
        return Response(rows, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        TradingSignal + SignalOutcome を ScoreProfile 単位・signal_type 単位で集計したサマリを返す。
        フィルタ:
        - ticker
        - signal_date_from
        - signal_date_to
        - score_profile_name
        - score_profile_version
        - signal_type
        """
        qs = build_summary_queryset(request.query_params)
        rows = summarize_signals(qs)
        return Response(rows, status=status.HTTP_200_OK)


class ScoreProfileViewSet(viewsets.ViewSet):
    """
    スコア設定プロファイルを扱う ViewSet（現時点では read-only）。
    """

    def list(self, request):
        """
        ScoreProfile のフル一覧を返す。
        エンドポイント: GET /api/v1/score-profiles/
        フェーズ22: proposal 由来 profile の source_proposal 情報を含む。
        """
        qs = (
            ScoreProfile.objects.prefetch_related("source_proposals")
            .order_by("-is_active", "-updated_at")
        )
        results = []
        for p in qs:
            source = p.source_proposals.order_by("-created_at").first()
            results.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "version": p.version,
                    "is_active": p.is_active,
                    "description": p.description or "",
                    "weights_json": p.weights_json,
                    "thresholds_json": p.thresholds_json,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    "source_proposal_id": source.id if source else None,
                    "source_proposal_name": source.proposal_name if source else None,
                    "source_proposal_status": source.status if source else None,
                }
            )
        return Response(results, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """
        単一の ScoreProfile 詳細を返す。
        エンドポイント: GET /api/v1/score-profiles/<id>/
        """
        try:
            p = ScoreProfile.objects.prefetch_related("source_proposals").get(pk=pk)
        except ScoreProfile.DoesNotExist:
            return Response(
                {"detail": "ScoreProfile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        source = p.source_proposals.order_by("-created_at").first()
        data = {
            "id": p.id,
            "name": p.name,
            "version": p.version,
            "is_active": p.is_active,
            "description": p.description or "",
            "weights_json": p.weights_json,
            "thresholds_json": p.thresholds_json,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "source_proposal_id": source.id if source else None,
            "source_proposal_name": source.proposal_name if source else None,
            "source_proposal_status": source.status if source else None,
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        """
        現在アクティブな ScoreProfile を返す。
        """
        profile = get_active_score_profile()
        data = {
            "id": profile.id,
            "name": profile.name,
            "version": profile.version,
            "is_active": profile.is_active,
            "description": profile.description,
            "weights_json": profile.weights_json,
            "thresholds_json": profile.thresholds_json,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        """
        指定 ScoreProfile を active に切り替える。
        エンドポイント: POST /api/v1/score-profiles/<id>/activate/
        """
        try:
            profile = ScoreProfile.objects.get(pk=pk)
        except ScoreProfile.DoesNotExist:
            return Response({"detail": "ScoreProfile not found."}, status=status.HTTP_404_NOT_FOUND)

        note = request.data.get("note") or ""
        profile = activate_score_profile(profile, note=note, activation_reason="manual_activate")

        data = {
            "id": profile.id,
            "name": profile.name,
            "version": profile.version,
            "is_active": profile.is_active,
            "description": profile.description,
            "weights_json": profile.weights_json,
            "thresholds_json": profile.thresholds_json,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="activation-history")
    def activation_history_list(self, request):
        """
        ScoreProfile の active 切替履歴一覧を返す。

        エンドポイント: GET /api/v1/score-profiles/activation-history/

        フィルタ:
        - activated_profile_id
        - source_proposal_id
        - activated_from=YYYY-MM-DD
        - activated_to=YYYY-MM-DD
        - activation_reason
        """
        qs = ScoreProfileActivationHistory.objects.select_related(
            "previous_profile",
            "activated_profile",
            "source_proposal",
        ).all()

        activated_profile_id = request.query_params.get("activated_profile_id")
        source_proposal_id = request.query_params.get("source_proposal_id")
        activated_from = request.query_params.get("activated_from")
        activated_to = request.query_params.get("activated_to")
        activation_reason = request.query_params.get("activation_reason")

        if activated_profile_id:
            qs = qs.filter(activated_profile_id=activated_profile_id)
        if source_proposal_id:
            qs = qs.filter(source_proposal_id=source_proposal_id)
        if activation_reason:
            qs = qs.filter(activation_reason=activation_reason)

        if activated_from:
            try:
                activated_from_date = date.fromisoformat(activated_from)
            except ValueError:
                return Response(
                    {"detail": "Invalid activated_from format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(activated_at__date__gte=activated_from_date)
        if activated_to:
            try:
                activated_to_date = date.fromisoformat(activated_to)
            except ValueError:
                return Response(
                    {"detail": "Invalid activated_to format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(activated_at__date__lte=activated_to_date)

        qs = qs.order_by("-activated_at", "-id")

        results = []
        for h in qs:
            previous_profile = h.previous_profile
            activated_profile = h.activated_profile
            source_proposal = h.source_proposal

            results.append(
                {
                    "id": h.id,
                    "previous_profile_id": previous_profile.id if previous_profile else None,
                    "previous_profile_name": (
                        previous_profile.name
                        if previous_profile is not None
                        else h.previous_profile_name_snapshot or None
                    ),
                    "previous_profile_version": (
                        previous_profile.version
                        if previous_profile is not None
                        else h.previous_profile_version_snapshot or None
                    ),
                    "activated_profile_id": activated_profile.id,
                    "activated_profile_name": (
                        activated_profile.name or h.activated_profile_name_snapshot or None
                    ),
                    "activated_profile_version": (
                        activated_profile.version
                        or h.activated_profile_version_snapshot
                        or None
                    ),
                    "source_proposal_id": source_proposal.id if source_proposal else None,
                    "source_proposal_name": (
                        source_proposal.proposal_name
                        if source_proposal is not None
                        else h.source_proposal_name_snapshot or None
                    ),
                    "activation_reason": h.activation_reason,
                    "note": h.note,
                    "activated_at": h.activated_at.isoformat() if h.activated_at else None,
                }
            )

        return Response(results, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="activation-history")
    def activation_history_for_profile(self, request, pk=None):
        """
        特定 ScoreProfile に関連する active 切替履歴を返す。

        エンドポイント: GET /api/v1/score-profiles/<id>/activation-history/

        対象 profile が:
        - activated_profile として登場した履歴
        - previous_profile として登場した履歴
        の両方を含む。
        """
        try:
            profile = ScoreProfile.objects.get(pk=pk)
        except ScoreProfile.DoesNotExist:
            return Response(
                {"detail": "ScoreProfile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = ScoreProfileActivationHistory.objects.select_related(
            "previous_profile",
            "activated_profile",
            "source_proposal",
        ).filter(
            models.Q(previous_profile_id=profile.id)
            | models.Q(activated_profile_id=profile.id)
        )
        qs = qs.order_by("-activated_at", "-id")

        results = []
        for h in qs:
            previous_profile = h.previous_profile
            activated_profile = h.activated_profile
            source_proposal = h.source_proposal

            results.append(
                {
                    "id": h.id,
                    "previous_profile_id": previous_profile.id if previous_profile else None,
                    "previous_profile_name": (
                        previous_profile.name
                        if previous_profile is not None
                        else h.previous_profile_name_snapshot or None
                    ),
                    "previous_profile_version": (
                        previous_profile.version
                        if previous_profile is not None
                        else h.previous_profile_version_snapshot or None
                    ),
                    "activated_profile_id": activated_profile.id,
                    "activated_profile_name": (
                        activated_profile.name or h.activated_profile_name_snapshot or None
                    ),
                    "activated_profile_version": (
                        activated_profile.version
                        or h.activated_profile_version_snapshot
                        or None
                    ),
                    "source_proposal_id": source_proposal.id if source_proposal else None,
                    "source_proposal_name": (
                        source_proposal.proposal_name
                        if source_proposal is not None
                        else h.source_proposal_name_snapshot or None
                    ),
                    "activation_reason": h.activation_reason,
                    "note": h.note,
                    "activated_at": h.activated_at.isoformat() if h.activated_at else None,
                }
            )

        return Response(results, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="rollback")
    def rollback(self, request):
        """
        現在 active な ScoreProfile を直前の profile にロールバックする。
        エンドポイント: POST /api/v1/score-profiles/rollback/
        入力: note（任意）
        """
        note = (request.data or {}).get("note") or ""
        try:
            profile = rollback_to_previous_profile(note=note)
        except RollbackNotAllowedError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        data = {
            "id": profile.id,
            "name": profile.name,
            "version": profile.version,
            "is_active": profile.is_active,
            "description": profile.description,
            "weights_json": profile.weights_json,
            "thresholds_json": profile.thresholds_json,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="review-targets")
    def review_targets(self, request):
        """
        レビュー対象の抽出。
        エンドポイント: GET /api/v1/score-profiles/review-targets/
        クエリ: signal_date_from, signal_date_to, threshold_success_rate, stale_days, min_evaluated_count
        """
        q = request.query_params
        signal_date_from = q.get("signal_date_from") or None
        signal_date_to = q.get("signal_date_to") or None
        try:
            threshold_success_rate = float(q.get("threshold_success_rate") or DEFAULT_THRESHOLD_SUCCESS_RATE)
        except (TypeError, ValueError):
            threshold_success_rate = DEFAULT_THRESHOLD_SUCCESS_RATE
        try:
            stale_days = int(q.get("stale_days") or DEFAULT_STALE_DAYS)
        except (TypeError, ValueError):
            stale_days = DEFAULT_STALE_DAYS
        try:
            min_evaluated_count = int(q.get("min_evaluated_count") or DEFAULT_MIN_EVALUATED_COUNT)
        except (TypeError, ValueError):
            min_evaluated_count = DEFAULT_MIN_EVALUATED_COUNT

        data = get_review_targets(
            signal_date_from=signal_date_from,
            signal_date_to=signal_date_to,
            threshold_success_rate=threshold_success_rate,
            stale_days=stale_days,
            min_evaluated_count=min_evaluated_count,
        )
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="compare")
    def compare(self, request):
        """
        base と candidate の2 profile を比較用サマリで返す。
        エンドポイント: GET /api/v1/score-profiles/compare/
        クエリ: base_profile_id, candidate_profile_id, signal_date_from, signal_date_to
        同じ profile 同士でも 200 で比較結果を返す。
        """
        base_id = request.query_params.get("base_profile_id")
        candidate_id = request.query_params.get("candidate_profile_id")
        if not base_id or not candidate_id:
            return Response(
                {"detail": "base_profile_id and candidate_profile_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            base_pk = int(base_id)
            candidate_pk = int(candidate_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "base_profile_id and candidate_profile_id must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        signal_date_from = request.query_params.get("signal_date_from") or None
        signal_date_to = request.query_params.get("signal_date_to") or None

        try:
            data = compare_profiles(
                base_pk,
                candidate_pk,
                signal_date_from=signal_date_from,
                signal_date_to=signal_date_to,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="ops-summary")
    def ops_summary(self, request):
        """
        運用向け ops-summary。
        エンドポイント: GET /api/v1/score-profiles/ops-summary/
        クエリ: signal_date_from, signal_date_to, threshold_success_rate, stale_days, min_evaluated_count
        """
        q = request.query_params
        signal_date_from = q.get("signal_date_from") or None
        signal_date_to = q.get("signal_date_to") or None
        try:
            threshold_success_rate = float(
                q.get("threshold_success_rate") or DEFAULT_THRESHOLD_SUCCESS_RATE
            )
        except (TypeError, ValueError):
            threshold_success_rate = DEFAULT_THRESHOLD_SUCCESS_RATE
        try:
            stale_days = int(q.get("stale_days") or DEFAULT_STALE_DAYS)
        except (TypeError, ValueError):
            stale_days = DEFAULT_STALE_DAYS
        try:
            min_evaluated_count = int(
                q.get("min_evaluated_count") or DEFAULT_MIN_EVALUATED_COUNT
            )
        except (TypeError, ValueError):
            min_evaluated_count = DEFAULT_MIN_EVALUATED_COUNT

        data = build_ops_summary(
            signal_date_from=signal_date_from,
            signal_date_to=signal_date_to,
            threshold_success_rate=threshold_success_rate,
            stale_days=stale_days,
            min_evaluated_count=min_evaluated_count,
        )
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="current/analysis-package")
    def current_analysis_package(self, request):
        """
        現在アクティブな ScoreProfile を対象に、
        AI 分析向けの入力パッケージ（summary + dataset）を返す。
        """
        package = build_analysis_package_for_active_profile(request.query_params)
        return Response(package, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="analysis-package")
    def analysis_package(self, request, pk=None):
        """
        指定 ScoreProfile (id) を対象に、
        AI 分析向けの入力パッケージ（summary + dataset）を返す。
        """
        profile = ScoreProfile.objects.get(pk=pk)
        package = build_analysis_package_for_profile(profile, request.query_params)
        return Response(package, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="current/ai-review")
    def current_ai_review(self, request):
        """
        現在アクティブな ScoreProfile を対象に、
        analysis-package をもとに AI による改善提案を取得する。

        この API 自体は AI の提案を DB に保存したり、自動適用したりはしない。
        """
        user_note = request.data.get("user_note")
        try:
            result = build_ai_review_for_active_profile(request.query_params, user_note=user_note)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="current/ai-review-and-save")
    def current_ai_review_and_save(self, request):
        """
        現在アクティブな ScoreProfile を対象に AI レビューを実行し、
        その結果を ScoreProfileProposal として保存して返す。
        """
        user_note = request.data.get("user_note")
        try:
            profile = get_active_score_profile()
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            ai_result = build_ai_review_for_profile(
                profile, request.query_params, user_note=user_note
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # analysis_package 側と同じキーセットから filters を抽出する
        filters = {
            k: v
            for k, v in request.query_params.items()
            if k in {"ticker", "signal_date_from", "signal_date_to", "signal_type"}
            and v not in ("", None)
        }

        proposal = save_profile_proposal(profile, filters, ai_result)

        data = {
            "proposal_id": proposal.id,
            "score_profile_id": proposal.score_profile_id,
            "proposal_name": proposal.proposal_name,
            "status": proposal.status,
            "score_profile_name_snapshot": proposal.score_profile_name_snapshot,
            "score_profile_version_snapshot": proposal.score_profile_version_snapshot,
            "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
            "analysis_summary": proposal.analysis_summary,
            "issues": proposal.issues_json,
            "improvement_hypotheses": proposal.improvement_hypotheses_json,
            "suggested_weights_json": proposal.suggested_weights_json,
            "suggested_thresholds_json": proposal.suggested_thresholds_json,
            "cautions": proposal.cautions_json,
        }
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="ai-review-and-save")
    def ai_review_and_save(self, request, pk=None):
        """
        指定 ScoreProfile (id) を対象に AI レビューを実行し、
        その結果を ScoreProfileProposal として保存して返す。
        """
        user_note = request.data.get("user_note")
        try:
            profile = ScoreProfile.objects.get(pk=pk)
        except ScoreProfile.DoesNotExist:
            return Response(
                {"detail": "ScoreProfile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            ai_result = build_ai_review_for_profile(
                profile, request.query_params, user_note=user_note
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        filters = {
            k: v
            for k, v in request.query_params.items()
            if k in {"ticker", "signal_date_from", "signal_date_to", "signal_type"}
            and v not in ("", None)
        }

        proposal = save_profile_proposal(profile, filters, ai_result)

        data = {
            "proposal_id": proposal.id,
            "score_profile_id": proposal.score_profile_id,
            "proposal_name": proposal.proposal_name,
            "status": proposal.status,
            "score_profile_name_snapshot": proposal.score_profile_name_snapshot,
            "score_profile_version_snapshot": proposal.score_profile_version_snapshot,
            "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
            "analysis_summary": proposal.analysis_summary,
            "issues": proposal.issues_json,
            "improvement_hypotheses": proposal.improvement_hypotheses_json,
            "suggested_weights_json": proposal.suggested_weights_json,
            "suggested_thresholds_json": proposal.suggested_thresholds_json,
            "cautions": proposal.cautions_json,
        }
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="proposals")
    def proposals(self, request, pk=None):
        """
        指定 ScoreProfile に紐づく ScoreProfileProposal 一覧を返す。
        エンドポイント: /api/v1/score-profiles/<id>/proposals/
        """
        try:
            profile = ScoreProfile.objects.get(pk=pk)
        except ScoreProfile.DoesNotExist:
            return Response(
                {"detail": "ScoreProfile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        proposals = profile.proposals.order_by("-created_at")
        results = []
        for p in proposals:
            results.append(
                {
                    "id": p.id,
                    "score_profile_id": p.score_profile_id,
                    "proposal_name": p.proposal_name,
                    "status": p.status,
                    "score_profile_name_snapshot": p.score_profile_name_snapshot,
                    "score_profile_version_snapshot": p.score_profile_version_snapshot,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
            )
        return Response(results, status=status.HTTP_200_OK)


class ProposalViewSet(viewsets.ViewSet):
    """
    ScoreProfileProposal の一覧・詳細取得用 ViewSet（read-only）。
    """

    def list(self, request):
        """
        ScoreProfileProposal の簡易一覧を返す。
        既存ルーティング `/api/v1/proposals/` を壊さないために保持しているが、
        プロファイル単位の一覧には `/api/v1/score-profiles/<id>/proposals/` を推奨する。
        """
        proposals = ScoreProfileProposal.objects.select_related("score_profile").order_by(
            "-created_at"
        )
        results = []
        for p in proposals:
            results.append(
                {
                    "id": p.id,
                    "score_profile_id": p.score_profile_id,
                    "proposal_name": p.proposal_name,
                    "status": p.status,
                    "score_profile_name_snapshot": p.score_profile_name_snapshot,
                    "score_profile_version_snapshot": p.score_profile_version_snapshot,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
            )
        return Response(results, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """
        単一の提案詳細を返す。
        """
        try:
            proposal = ScoreProfileProposal.objects.get(pk=pk)
        except ScoreProfileProposal.DoesNotExist:
            return Response(
                {"detail": "ScoreProfileProposal not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = {
            "id": proposal.id,
            "score_profile_id": proposal.score_profile_id,
            "proposal_name": proposal.proposal_name,
            "status": proposal.status,
            "score_profile_name_snapshot": proposal.score_profile_name_snapshot,
            "score_profile_version_snapshot": proposal.score_profile_version_snapshot,
            "source_filters": proposal.source_filters_json,
            "analysis_summary": proposal.analysis_summary,
            "issues": proposal.issues_json,
            "improvement_hypotheses": proposal.improvement_hypotheses_json,
            "suggested_weights_json": proposal.suggested_weights_json,
            "suggested_thresholds_json": proposal.suggested_thresholds_json,
            "cautions": proposal.cautions_json,
            "raw_ai_response_json": proposal.raw_ai_response_json,
            "review_note": proposal.review_note,
            "applied_score_profile_id": proposal.applied_score_profile_id,
            "applied_score_profile_name": (
                proposal.applied_score_profile.name if proposal.applied_score_profile else None
            ),
            "applied_score_profile_version": (
                proposal.applied_score_profile.version if proposal.applied_score_profile else None
            ),
            "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
            "updated_at": proposal.updated_at.isoformat() if proposal.updated_at else None,
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="review")
    def review(self, request, pk=None):
        """
        proposal のレビュー情報（status, review_note）のみを更新する。
        エンドポイント: PATCH /api/v1/proposals/<id>/review/
        """
        try:
            proposal = ScoreProfileProposal.objects.get(pk=pk)
        except ScoreProfileProposal.DoesNotExist:
            return Response(
                {"detail": "ScoreProfileProposal not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        status_value = request.data.get("status")
        review_note = request.data.get("review_note")

        # 不正なフィールドが含まれていたら 400 にする方針
        allowed_keys = {"status", "review_note"}
        extra_keys = set(request.data.keys()) - allowed_keys
        if extra_keys:
            return Response(
                {"detail": f"Unsupported fields for review: {sorted(extra_keys)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if status_value is None and review_note is None:
            return Response(
                {"detail": "At least one of 'status' or 'review_note' must be provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if status_value is not None:
            try:
                validate_status(status_value)
            except Exception as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        proposal = update_review_fields(
            proposal,
            status=status_value,
            review_note=review_note,
        )

        data = {
            "id": proposal.id,
            "score_profile_id": proposal.score_profile_id,
            "status": proposal.status,
            "review_note": proposal.review_note,
        }
        return Response(data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        """
        proposal の削除。
        ルール:
        - draft, rejected: 削除可
        - reviewed, accepted: 削除不可（409 Conflict）
        """
        try:
            proposal = ScoreProfileProposal.objects.get(pk=pk)
        except ScoreProfileProposal.DoesNotExist:
            return Response(
                {"detail": "ScoreProfileProposal not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not can_delete(proposal):
            return Response(
                {"detail": f"Proposal with status '{proposal.status}' cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )

        proposal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="apply")
    def apply(self, request, pk=None):
        """
        accepted 済み proposal から新しい ScoreProfile を生成する。
        エンドポイント: POST /api/v1/proposals/<id>/apply/
        """
        try:
            proposal = ScoreProfileProposal.objects.get(pk=pk)
        except ScoreProfileProposal.DoesNotExist:
            return Response(
                {"detail": "ScoreProfileProposal not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            profile = apply_proposal_to_new_profile(proposal)
        except ValidationError as exc:
            # 状態衝突系（accepted でない / すでに applied 済み）を 409 にマッピング
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            # 入力不正（suggested_* が空・不正など）は 400
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        data = {
            "id": profile.id,
            "name": profile.name,
            "version": profile.version,
            "is_active": profile.is_active,
            "description": profile.description,
            "weights_json": profile.weights_json,
            "thresholds_json": profile.thresholds_json,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="ai-review")
    def ai_review(self, request, pk=None):
        """
        指定 ScoreProfile (id) を対象に、
        analysis-package をもとに AI による改善提案を取得する。
        """
        user_note = request.data.get("user_note")
        try:
            profile = ScoreProfile.objects.get(pk=pk)
        except ScoreProfile.DoesNotExist:
            return Response({"detail": "ScoreProfile not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = build_ai_review_for_profile(profile, request.query_params, user_note=user_note)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(result, status=status.HTTP_200_OK)

