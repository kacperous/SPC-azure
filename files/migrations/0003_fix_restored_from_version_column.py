from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("files", "0002_userfileversion"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE files_userfileversion
            ADD COLUMN IF NOT EXISTS restored_from_version integer NULL;
            """,
            reverse_sql="""
            ALTER TABLE files_userfileversion
            DROP COLUMN IF EXISTS restored_from_version;
            """,
        ),
    ]
