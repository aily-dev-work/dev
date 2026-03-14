"""
SQLite 利用時に WAL モードと busy_timeout を設定し、database is locked を軽減する。
"""
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def set_sqlite_pragmas(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")  # 30秒（ミリ秒指定）
        cursor.close()
