"""
5 分毎の自動実行用: 全監視銘柄の 5 分足を取得し、取得ごとにテクニカル・スコアを計算してシグナルを保存する。

使い方:
  python manage.py run_5m_fetch_and_evaluate

cron 例（5 分毎）:
  */5 * * * * cd /path/to/project && python manage.py run_5m_fetch_and_evaluate
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from stocks.models import WatchStock
from stocks.services.price_fetcher import fetch_and_save_5m_prices
from stocks.services.signal_generation import generate_trading_signal_5m
from stocks.services.signal_scoring import score_from_technical
from stocks.services.technical_analysis import calculate_technical_summary_5m


def _round_to_5min_bar(dt):
    """現在時刻を 5 分足のバー開始時刻に切り捨てる。"""
    minute = (dt.minute // 5) * 5
    return dt.replace(minute=minute, second=0, microsecond=0)


class Command(BaseCommand):
    help = "全監視銘柄の 5 分足を取得し、各銘柄でテクニカル・スコア判定してシグナルを保存する（5 分毎実行想定）。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-fetch",
            action="store_true",
            help="5 分足の取得をスキップし、既存データだけで判定のみ行う",
        )

    def handle(self, *args, **options):
        skip_fetch = options.get("no_fetch", False)
        stocks = list(WatchStock.objects.filter(is_active=True).exclude(ticker="").exclude(ticker__isnull=True))
        if not stocks:
            self.stdout.write("監視対象銘柄がありません。")
            return

        bar_start = _round_to_5min_bar(timezone.now())

        total_fetched = 0
        signals_created = 0

        for stock in stocks:
            if not skip_fetch:
                try:
                    created = fetch_and_save_5m_prices(stock)
                    total_fetched += created
                except Exception as e:
                    self.stderr.write(f"fetch 5m failed {stock.ticker}: {e}")
                    continue

            try:
                summary = calculate_technical_summary_5m(stock)
            except Exception as e:
                self.stderr.write(f"technical_5m failed {stock.ticker}: {e}")
                continue

            if summary.latest_close is None:
                continue

            try:
                score_result = score_from_technical(summary)
            except Exception as e:
                self.stderr.write(f"score failed {stock.ticker}: {e}")
                continue

            try:
                generate_trading_signal_5m(stock, summary, score_result, bar_start)
                signals_created += 1
            except Exception as e:
                self.stderr.write(f"signal_5m failed {stock.ticker}: {e}")

        self.stdout.write(
            f"done: stocks={len(stocks)} 5m_created={total_fetched} signals_updated={signals_created} bar_start={bar_start.isoformat()}"
        )
