from django.db import migrations, models


def create_initial_score_profile(apps, schema_editor):
    ScoreProfile = apps.get_model("stocks", "ScoreProfile")

    weights = {
        "buy": {
            "trend_long_up": 20.0,
            "trend_mid_up": 15.0,
            "trend_short_up": 10.0,
            "volume_high": 10.0,
            "above_ma25": 10.0,
            "above_ma75": 10.0,
            "near_high_20": 10.0,
            "near_low_20": 10.0,
        },
        "sell": {
            "trend_long_down": 20.0,
            "trend_mid_down": 15.0,
            "trend_short_down": 10.0,
            "volume_low": 10.0,
            "below_ma25": 10.0,
            "below_ma75": 10.0,
            "near_low_20": 10.0,
            "near_high_20": 10.0,
        },
    }

    thresholds = {
        "bias": {
            "neutral_abs_diff_lt": 10.0,
        },
        "strength": {
            "weak_abs_diff_lt": 15.0,
            "normal_abs_diff_lt": 30.0,
        },
    }

    ScoreProfile.objects.create(
        name="Default scoring profile",
        version="v1",
        is_active=True,
        description="Initial profile migrated from hardcoded signal_scoring.py (Phase 4).",
        weights_json=weights,
        thresholds_json=thresholds,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("stocks", "0005_signaloutcome"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScoreProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("version", models.CharField(help_text="バージョン識別子（例: 'v1', '2026-03-13-01' など）", max_length=32)),
                ("is_active", models.BooleanField(default=False, help_text="現在のスコア計算に利用する有効プロファイルかどうか")),
                ("description", models.TextField(blank=True, help_text="このプロファイルの用途やメモ（任意）")),
                ("weights_json", models.JSONField(help_text="買い/売りスコアの重み定義（例: {'buy': {...}, 'sell': {...}}）")),
                ("thresholds_json", models.JSONField(help_text="バイアス・強度などの閾値定義")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "スコア設定プロファイル",
                "verbose_name_plural": "スコア設定プロファイル",
                "ordering": ["-is_active", "-updated_at"],
            },
        ),
        migrations.RunPython(create_initial_score_profile, migrations.RunPython.noop),
    ]

