# chatbot/apps.py
from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chatbot"

    def ready(self):
        # Dữ liệu sẽ được tải khi cần thiết thay vì tại thời điểm khởi động
        # để tránh làm chậm quá trình khởi động Django
        pass
