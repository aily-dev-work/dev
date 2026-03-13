from rest_framework import viewsets

from .models import WatchStock
from .serializers import WatchStockSerializer


class WatchStockViewSet(viewsets.ModelViewSet):
    """
    WatchStock の CRUD を行う ViewSet。
    フェーズ1では認証・権限制御は行わず、最小構成とする。
    """

    queryset = WatchStock.objects.all()
    serializer_class = WatchStockSerializer

