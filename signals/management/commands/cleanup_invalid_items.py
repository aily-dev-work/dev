from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from signals.models import DetectedItem, TrackedProduct
from signals.services import looks_like_product_name


class Command(BaseCommand):
    help = "Delete detected items and tracked products that are clearly not product candidates."

    def handle(self, *args, **options):
        removed_items = 0
        removed_products = 0

        with transaction.atomic():
            invalid_product_ids = []
            for product in TrackedProduct.objects.all().select_related():
                if not looks_like_product_name(product.name):
                    invalid_product_ids.append(product.id)

            if invalid_product_ids:
                removed_items, _ = DetectedItem.objects.filter(product_id__in=invalid_product_ids).delete()
                removed_products, _ = TrackedProduct.objects.filter(id__in=invalid_product_ids).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"cleanup complete: removed_items={removed_items} removed_products={removed_products}"
            )
        )
