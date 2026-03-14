from rest_framework.routers import DefaultRouter

from .views import (
    ProposalViewSet,
    ScoreProfileViewSet,
    SignalViewSet,
    StockPrice5MinViewSet,
    StockPriceDailyViewSet,
    StockPriceMonthlyViewSet,
    WatchStockViewSet,
)

app_name = "stocks"

router = DefaultRouter()
router.register("stocks", WatchStockViewSet, basename="watchstock")
router.register("stock-prices", StockPriceDailyViewSet, basename="stockpricedaily")
router.register("stock-prices-5m", StockPrice5MinViewSet, basename="stockprice5m")
router.register("stock-prices-monthly", StockPriceMonthlyViewSet, basename="stockpricemonthly")
router.register("signals", SignalViewSet, basename="signal")
router.register("score-profiles", ScoreProfileViewSet, basename="scoreprofile")
router.register("proposals", ProposalViewSet, basename="proposal")

urlpatterns = router.urls

