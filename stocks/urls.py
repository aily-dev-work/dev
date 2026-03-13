from rest_framework.routers import DefaultRouter

from .views import WatchStockViewSet

app_name = "stocks"

router = DefaultRouter()
router.register("stocks", WatchStockViewSet, basename="watchstock")

urlpatterns = router.urls

