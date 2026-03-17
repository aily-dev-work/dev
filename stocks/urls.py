from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    MarketSearchView,
    ProposalViewSet,
    Run5mEvaluateView,
    CronPingView,
    ScoreProfileViewSet,
    SignalViewSet,
    StockPrice5MinViewSet,
    StockPriceDailyViewSet,
    StockPriceMonthlyViewSet,
    StockPriceWeeklyViewSet,
    WatchStockViewSet,
)

app_name = "stocks"

router = DefaultRouter()
router.register("stocks", WatchStockViewSet, basename="watchstock")
router.register("stock-prices", StockPriceDailyViewSet, basename="stockpricedaily")
router.register("stock-prices-5m", StockPrice5MinViewSet, basename="stockprice5m")
router.register("stock-prices-monthly", StockPriceMonthlyViewSet, basename="stockpricemonthly")
router.register("stock-prices-weekly", StockPriceWeeklyViewSet, basename="stockpriceweekly")
router.register("signals", SignalViewSet, basename="signal")
router.register("score-profiles", ScoreProfileViewSet, basename="scoreprofile")
router.register("proposals", ProposalViewSet, basename="proposal")

urlpatterns = [
    path("market-search/", MarketSearchView.as_view(), name="market-search"),
    path("cron/run-5m-evaluate/", Run5mEvaluateView.as_view(), name="cron-run-5m-evaluate"),
    path("cron/ping/", CronPingView.as_view(), name="cron-ping"),
    # DRF の router に依存せず、明示的に scores アクションのパスを配線しておく
    path(
        "stocks/scores/",
        WatchStockViewSet.as_view({"get": "scores"}),
        name="watchstock-scores",
    ),
] + router.urls

