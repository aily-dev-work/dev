from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stocks", "0009_scoreprofileproposal"),
    ]

    operations = [
        migrations.AddField(
            model_name="scoreprofileproposal",
            name="review_note",
            field=models.TextField(
                blank=True,
                default="",
                help_text="人間によるレビューコメントやメモ",
            ),
        ),
    ]

