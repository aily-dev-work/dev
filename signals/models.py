from django.db import models


class WatchSource(models.Model):
    SOURCE_TYPE_RSS = "rss"
    SOURCE_TYPE_HTML = "html"

    SOURCE_TYPE_CHOICES = (
        (SOURCE_TYPE_RSS, "RSS"),
        (SOURCE_TYPE_HTML, "HTML"),
    )

    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "name"]
        verbose_name = "監視サイト"
        verbose_name_plural = "監視サイト"

    def __str__(self) -> str:
        return self.name


class SignalKeyword(models.Model):
    keyword = models.CharField(max_length=100, unique=True)
    score = models.PositiveIntegerField(default=0)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-score", "keyword"]
        verbose_name = "検知キーワード"
        verbose_name_plural = "検知キーワード"

    def __str__(self) -> str:
        return f"{self.keyword} ({self.score})"


class DetectedItem(models.Model):
    source = models.ForeignKey(WatchSource, on_delete=models.CASCADE, related_name="detected_items")
    title = models.CharField(max_length=500)
    url = models.URLField(unique=True)
    summary = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    matched_keywords = models.JSONField(default=list, blank=True)
    total_score = models.PositiveIntegerField(default=0)
    is_alert = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "検知記事"
        verbose_name_plural = "検知記事"

    def __str__(self) -> str:
        return self.title
