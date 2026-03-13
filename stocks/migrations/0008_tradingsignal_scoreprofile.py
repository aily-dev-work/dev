from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stocks", "0007_alter_scoreprofile_id_alter_signaloutcome_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tradingsignal",
            name="score_profile",
            field=models.ForeignKey(
                blank=True,
                help_text="このシグナル生成時に使用したスコアプロファイル",
                null=True,
                on_delete=models.SET_NULL,
                related_name="signals",
                to="stocks.scoreprofile",
            ),
        ),
        migrations.AddField(
            model_name="tradingsignal",
            name="score_profile_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="生成時点の ScoreProfile.name スナップショット",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="tradingsignal",
            name="score_profile_version",
            field=models.CharField(
                blank=True,
                default="",
                help_text="生成時点の ScoreProfile.version スナップショット",
                max_length=32,
            ),
        ),
    ]

