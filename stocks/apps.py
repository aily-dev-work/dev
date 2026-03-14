from django.apps import AppConfig


class StocksConfig(AppConfig):
    name = "stocks"

    def ready(self):
        import stocks.signals  # noqa: F401  # SQLite WAL / busy_timeout を有効化
