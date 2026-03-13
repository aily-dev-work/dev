from rest_framework.routers import DefaultRouter

from .views import SignalViewSet, StockPriceDailyViewSet, WatchStockViewSet

app_name = "stocks"

router = DefaultRouter()
router.register("stocks", WatchStockViewSet, basename="watchstock")
router.register("stock-prices", StockPriceDailyViewSet, basename="stockpricedaily")
router.register("signals", SignalViewSet, basename="signal")

urlpatterns = router.urls

