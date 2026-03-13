from rest_framework import viewsets

from .models import StockPriceDaily, WatchStock
from .serializers import StockPriceDailySerializer, WatchStockSerializer


class WatchStockViewSet(viewsets.ModelViewSet):
    """
    WatchStock の CRUD を行う ViewSet。
    フェーズ1では認証・権限制御は行わず、最小構成とする。
    """

    queryset = WatchStock.objects.all()
    serializer_class = WatchStockSerializer


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

