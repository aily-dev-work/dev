"""
5 分毎の自動実行用: 全監視銘柄の 5 分足を取得し、取得ごとにテクニカル・スコアを計算してシグナルを保存する。

使い方:
  python manage.py run_5m_fetch_and_evaluate

cron 例（5 分毎）:
  */5 * * * * cd /path/to/project && python manage.py run_5m_fetch_and_evaluate

クラウドでは HTTP エンドポイント POST /api/v1/cron/run-5m-evaluate/ を 5 分毎に呼ぶ方法も利用可能（docs/CRON_CLOUD.md 参照）。
"""
from django.core.management.base import BaseCommand

from stocks.services.run_5m_job import run_5m_fetch_and_evaluate


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
        result = run_5m_fetch_and_evaluate(skip_fetch=skip_fetch)
        for err in result["errors"]:
            self.stderr.write(err)
        self.stdout.write(
            f"done: stocks={result['stocks_count']} 5m_created={result['5m_created']} "
            f"signals_updated={result['signals_updated']} bar_start={result['bar_start']}"
        )
