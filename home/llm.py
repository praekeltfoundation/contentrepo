from typing import Optional
import json

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import parsers, renderers
from rest_framework import serializers
import openai

from .models import ContentPage
from .utils import (
    generate_id,
    retrieve_top_n_content_pieces,
    web_content,
    whatsapp_content,
    messenger_content,
    viber_content,
)


class LLMRequestSerializer(serializers.Serializer):
    chat_model = serializers.CharField(
        label="OpenAI chat model (default 'gpt-3.5-turbo')", write_only=True
    )
    system_prompt = serializers.CharField(label="System prompt", write_only=True)
    user_prompt = serializers.CharField(label="User prompt", write_only=True)
    temperature = serializers.FloatField(
        label="Temperature", default=0.7, write_only=True
    )
    max_tokens = serializers.IntegerField(
        label="Max tokens", default=None, write_only=True
    )
    session_id = serializers.CharField(
        label="Session ID (default generated)", write_only=True
    )
    platform = serializers.CharField(label="Platform", default="web", write_only=True)


class LLMChatViewSet(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = LLMRequestSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request):
        chat_model = request.data.get("chat_model", "gpt-3.5-turbo")
        system_prompt = request.data.get(
            "system_prompt",
            "You are a chatbot that answers questions based on the context provided.",
        )
        user_prompt = request.data.get("user_prompt")
        temperature = request.data.get("temperature", 0.7)
        max_tokens = request.data.get("max_tokens", None)
        session_id = request.data.get("session_id") or generate_id()
        platform = request.data.get("platform", "web")

        language_response = detect_languages_chain(
            chat_model=chat_model,
            user_prompt=user_prompt,
        )

        prompt_response = conversation_chain(
            chat_model=chat_model,
            system_prompt=system_prompt,
            untranslated_user_prompt=user_prompt,
            translated_user_prompt=language_response.get(
                "translation_to_english", user_prompt
            ),
            language=language_response.get("primary_detected_language", None),
            temperature=temperature,
            max_tokens=max_tokens,
            session_id=session_id,
            platform=platform,
        )

        return Response(
            {
                "session_id": session_id,
                "response": prompt_response,
                "language": language_response,
            }
        )


def detect_languages_chain(chat_model: str, user_prompt: str):
    response = openai.ChatCompletion.create(
        model=chat_model,
        messages=[
            {
                "role": "system",
                "content": "You are an optimized language detection bot that detects languages in textual input. Your results will be used in downstream natural language processing.",
            },
            {
                "role": "user",
                "content": f"Detect the languages in this text: {user_prompt}",
            },
        ],
        temperature=0,
        function_call="auto",
        functions=[
            {
                "name": "detect_languages",
                "description": "Detecting language and other insights on the user's prompt.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "primary_detected_language": {
                            "title": "Primary language",
                            "description": "The primary detected language (e.g. English, French, Zulu, etc.))",
                            "type": "string",
                        },
                        "detection_confidence": {
                            "title": "Confidence",
                            "description": "Confidence level of the language detection from scale of 0 to 1",
                            "type": "number",
                        },
                        "secondary_detected_languages": {
                            "title": "Secondary languages",
                            "description": "Command separated list of secondary languages detected if any",
                            "type": "string",
                        },
                        "translation_to_english": {
                            "title": "English translation",
                            "description": "English translation of the user input text if not in English",
                            "type": "string",
                        },
                        "translation_confidence": {
                            "title": "Confidence",
                            "description": "Confidence level of the language translation to English from scale of 0 to 1",
                            "type": "number",
                        },
                        "has_english_words": {
                            "title": "If the user input text has any English words",
                            "description": "Whether the input text has English words",
                            "type": "boolean",
                        },
                    },
                    "required": [
                        "primary_detected_language",
                        "detection_confidence",
                        "translation_to_english",
                        "translation_confidence",
                        "has_english_words",
                    ],
                },
            }
        ],
    )

    response_message = response["choices"][0]["message"]

    if response_message.get("function_call"):
        function_args = json.loads(response_message["function_call"]["arguments"])
        return function_args
    return {}


def conversation_chain(
    chat_model: str,
    system_prompt: str,
    untranslated_user_prompt: str,
    translated_user_prompt: str,  # translated to English
    language: str,
    temperature: float,
    max_tokens: Optional[int],
    session_id: str,
    platform: str,
):
    context = fetch_embeddings_content(
        untranslated_prompt=untranslated_user_prompt,
        translated_prompt=translated_user_prompt,
        platform=platform,
    )
    response = openai.ChatCompletion.create(
        model=chat_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "system",
                "content": system_prompt.strip(),
            },
            *fetch_conversation_history(session_id),
            {
                "role": "user",
                "content": f"""
                Try your best to use the following pieces of context to answer the question at the end if possible.

                Context:
                {context}

                Question: What does The World Bank do?

                Answer in English: The World Bank is an international financial institution that provides loans and grants to countries for the purpose of promoting economic development and reducing poverty. It also offers technical assistance and policy advice to help countries implement effective strategies for sustainable growth.

                Question: {untranslated_user_prompt}

                Answer in {language}:
                """.strip(),
            },
        ],
    )

    return response["choices"][0]["message"]


def fetch_conversation_history(session_id):
    # TODO: Fetch conversation history from database with session id and parse it into the format that OpenAI API expects
    return []


def fetch_embeddings_content(untranslated_prompt, translated_prompt, platform):
    queryset = ContentPage.objects.live().prefetch_related("locale")
    ids = retrieve_top_n_content_pieces(
        user_input=f"{untranslated_prompt} {translated_prompt}",
        queryset=queryset,
        platform=platform,
    )
    queryset = queryset.filter(id__in=ids)

    content = None
    if platform == "web":
        content = [web_content(p) for p in queryset]
    elif platform == "whatsapp":
        content = [whatsapp_content(p) for p in queryset]
    elif platform == "messenger":
        content = [messenger_content(p) for p in queryset]
    elif platform == "viber":
        content = [viber_content(p) for p in queryset]

    return "\n".join(content)


llm_chat = LLMChatViewSet.as_view()
