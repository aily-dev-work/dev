from django.core.management.base import BaseCommand

from signals.models import SignalKeyword


DEFAULT_KEYWORDS = [
    ("限定", 20, "限定販売・限定版の検知"),
    ("受注終了", 40, "受注終了の検知"),
    ("生産終了", 50, "生産終了の検知"),
    ("再販なし", 50, "再販予定なしの検知"),
    ("再販未定", 30, "再販未定の検知"),
    ("抽選販売", 30, "抽選販売の検知"),
    ("完売", 35, "完売の検知"),
    ("在庫切れ", 35, "在庫切れの検知"),
    ("販売終了", 40, "販売終了の検知"),
    ("予約終了", 35, "予約終了の検知"),
]


class Command(BaseCommand):
    help = "Default keywords for premium score detection."

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0
        for keyword, score, description in DEFAULT_KEYWORDS:
            obj, created = SignalKeyword.objects.get_or_create(
                keyword=keyword,
                defaults={
                    "score": score,
                    "description": description,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"created: {keyword} ({score})"))
            else:
                skipped_count += 1
                self.stdout.write(f"skipped: {obj.keyword} already exists")

        self.stdout.write(
            self.style.SUCCESS(
                f"done: created={created_count} skipped={skipped_count}"
            )
        )
