from django.core.management.base import BaseCommand

from signals.models import TrackedProduct, WatchSource
from signals.services import process_source


class Command(BaseCommand):
    help = "Fetch RSS/HTML sources and store detected items."

    def handle(self, *args, **options):
        if not TrackedProduct.objects.filter(is_active=True).exists():
            self.stdout.write(self.style.WARNING("no active products found"))
            return

        sources = WatchSource.objects.filter(is_active=True).order_by("name")
        if not sources.exists():
            self.stdout.write(self.style.WARNING("no active sources found"))
            return

        total_created = 0
        total_matched = 0
        total_skipped = 0

        for source in sources:
            try:
                self.stdout.write(f"[START] {source.name} ({source.source_type}) {source.url}")
                result = process_source(source)
                total_created += result["created"]
                total_matched += result["matched"]
                total_skipped += result["skipped"]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[DONE] {source.name}: entries={result['entries']} created={result['created']} matched={result['matched']} skipped={result['skipped']} unmatched_products={result['unmatched_products']}"
                    )
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"[ERROR] {source.name}: {exc}")
                )
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"summary: created={total_created} matched={total_matched} skipped={total_skipped}"
            )
        )
