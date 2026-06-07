from django.urls import path

from .views import (
    FetchSignalsView,
    HomeView,
    ItemDetailView,
    KeywordListView,
    SourceCreateView,
    SourceListView,
)


app_name = "signals"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("items/<int:pk>/", ItemDetailView.as_view(), name="item-detail"),
    path("sources/", SourceListView.as_view(), name="source-list"),
    path("sources/new/", SourceCreateView.as_view(), name="source-create"),
    path("keywords/", KeywordListView.as_view(), name="keyword-list"),
    path("fetch-signals/", FetchSignalsView.as_view(), name="fetch-signals"),
]
