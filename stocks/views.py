from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import StockPriceDaily, WatchStock
from .serializers import StockPriceDailySerializer, WatchStockSerializer
from .services.technical_analysis import calculate_technical_summary
from .services.signal_scoring import score_from_technical


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

