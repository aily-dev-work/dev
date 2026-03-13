from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ScoreProfile, SignalOutcome, StockPriceDaily, TradingSignal, WatchStock
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

    @action(detail=True, methods=["post"], url_path="ai-review")
    def ai_review(self, request, pk=None):
        """
        指定 ScoreProfile (id) を対象に、
        analysis-package をもとに AI による改善提案を取得する。
        """
        user_note = request.data.get("user_note")
        profile = ScoreProfile.objects.get(pk=pk)

        try:
            result = build_ai_review_for_profile(profile, request.query_params, user_note=user_note)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(result, status=status.HTTP_200_OK)

