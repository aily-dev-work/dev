from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("stocks", "0011_alter_scoreprofile_id_alter_signaloutcome_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="scoreprofileproposal",
            name="applied_score_profile",
            field=models.ForeignKey(
                to="stocks.scoreprofile",
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_proposals",
                help_text="この proposal から生成された ScoreProfile（なければ NULL）",
            ),
        ),
    ]

