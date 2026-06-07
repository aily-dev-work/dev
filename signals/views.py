from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from .forms import WatchSourceForm
from .models import DetectedItem, SignalKeyword, TrackedProduct, WatchSource
from .services import process_source


class HomeView(ListView):
    model = DetectedItem
    template_name = "signals/home.html"
    context_object_name = "items"
    paginate_by = 50

    def get_queryset(self):
        return (
            DetectedItem.objects.select_related("source", "product")
            .filter(product__isnull=False)
            .order_by("-published_at", "-created_at")
        )


class ItemDetailView(DetailView):
    model = DetectedItem
    template_name = "signals/item_detail.html"
    context_object_name = "item"


class SourceListView(ListView):
    model = WatchSource
    template_name = "signals/source_list.html"
    context_object_name = "sources"


class SourceCreateView(CreateView):
    model = WatchSource
    form_class = WatchSourceForm
    template_name = "signals/source_form.html"
    success_url = reverse_lazy("signals:source-list")

    def form_valid(self, form):
        messages.success(self.request, "監視サイトを登録しました。")
        return super().form_valid(form)


class KeywordListView(ListView):
    model = SignalKeyword
    template_name = "signals/keyword_list.html"
    context_object_name = "keywords"


class ProductListView(ListView):
    model = TrackedProduct
    template_name = "signals/product_list.html"
    context_object_name = "products"


class FetchSignalsView(View):
    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        sources = WatchSource.objects.filter(is_active=True).order_by("name")
        if not sources.exists():
            messages.warning(request, "有効な監視サイトがありません。先に監視サイトを登録してください。")
            return redirect("signals:home")

        total_created = 0
        total_matched = 0
        total_skipped = 0
        total_errors = 0
        total_unmatched_products = 0
        total_discovered_products = 0

        for source in sources:
            try:
                result = process_source(source)
                total_created += result["created"]
                total_matched += result["matched"]
                total_skipped += result["skipped"]
                total_unmatched_products += result["unmatched_products"]
                total_discovered_products += result["discovered_products"]
                messages.success(
                    request,
                    f"{source.name}: created={result['created']} matched={result['matched']} skipped={result['skipped']} discovered_products={result['discovered_products']} unmatched_products={result['unmatched_products']}",
                )
            except Exception as exc:
                total_errors += 1
                messages.error(request, f"{source.name}: {exc}")

        messages.info(
            request,
            f"巡回完了: created={total_created} matched={total_matched} skipped={total_skipped} discovered_products={total_discovered_products} unmatched_products={total_unmatched_products} errors={total_errors}",
        )
        return redirect("signals:home")
