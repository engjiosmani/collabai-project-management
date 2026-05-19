from rest_framework import serializers


class ChatBotHistoryItemSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=('user', 'assistant'))
    content = serializers.CharField(max_length=8000)


class ChatBotRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000)
    history = ChatBotHistoryItemSerializer(many=True, required=False, default=list)


class ChatBotResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    request_id = serializers.IntegerField()
