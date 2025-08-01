# chatbot/urls.py
from django.urls import path
from .views import chat_endpoint
from chatbot import views

app_name = "chatbot"

urlpatterns = [
    path("", views.chatbot_view, name="chatbot_interface"),
    path("get-response/", views.get_chatbot_response, name="get_chatbot_response"),
    path("api/chat/", chat_endpoint, name="chat-endpoint"),
]
