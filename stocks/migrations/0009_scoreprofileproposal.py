from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("stocks", "0008_tradingsignal_scoreprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScoreProfileProposal",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "proposal_name",
                    models.CharField(
                        help_text="人間が識別しやすい提案名（自動生成されたデフォルト名を含む）",
                        max_length=255,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "draft"),
                            ("reviewed", "reviewed"),
                            ("accepted", "accepted"),
                            ("rejected", "rejected"),
                        ],
                        default="draft",
                        help_text="提案のレビュー状態",
                        max_length=16,
                    ),
                ),
                (
                    "score_profile_name_snapshot",
                    models.CharField(
                        help_text="提案作成時点の ScoreProfile.name スナップショット",
                        max_length=100,
                    ),
                ),
                (
                    "score_profile_version_snapshot",
                    models.CharField(
                        help_text="提案作成時点の ScoreProfile.version スナップショット",
                        max_length=32,
                    ),
                ),
                (
                    "source_filters_json",
                    models.JSONField(
                        help_text="analysis-package 生成時に利用したフィルター条件（ticker, 日付範囲など）",
                    ),
                ),
                (
                    "analysis_summary",
                    models.TextField(help_text="AI による全体サマリテキスト"),
                ),
                (
                    "issues_json",
                    models.JSONField(help_text="AI が指摘した課題一覧"),
                ),
                (
                    "improvement_hypotheses_json",
                    models.JSONField(help_text="AI が提案する改善仮説一覧"),
                ),
                (
                    "suggested_weights_json",
                    models.JSONField(
                        help_text="AI が提案する新しい weights_json",
                    ),
                ),
                (
                    "suggested_thresholds_json",
                    models.JSONField(
                        help_text="AI が提案する新しい thresholds_json",
                    ),
                ),
                (
                    "cautions_json",
                    models.JSONField(help_text="AI が提示する注意点・リスク"),
                ),
                (
                    "raw_ai_response_json",
                    models.JSONField(
                        help_text="AI から返却された生の JSON 応答（将来の解析用）",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "score_profile",
                    models.ForeignKey(
                        help_text="提案の対象となる ScoreProfile",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="proposals",
                        to="stocks.scoreprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "スコア設定プロファイル提案",
                "verbose_name_plural": "スコア設定プロファイル提案",
                "ordering": ["-created_at"],
            },
        ),
    ]

