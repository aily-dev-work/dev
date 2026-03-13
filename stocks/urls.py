from rest_framework.routers import DefaultRouter

from .views import StockPriceDailyViewSet, WatchStockViewSet

app_name = "stocks"

router = DefaultRouter()
router.register("stocks", WatchStockViewSet, basename="watchstock")
router.register("stock-prices", StockPriceDailyViewSet, basename="stockpricedaily")

urlpatterns = router.urls

