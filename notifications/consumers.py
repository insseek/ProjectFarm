# 【channels】（第4步）创建应用的消费者
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json


class AsyncConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        self.group_name = 'group_name'
        super().__init__(*args, **kwargs)

    async def connect(self):  # 连接时触发
        self.group_name = self.scope['url_route']['kwargs']['group_name']
        # self.room_group_name = 'chat_test'
        # 将新的连接加入到群组
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):  # 断开时触发
        # 将关闭的连接从群组中移除
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data=None, bytes_data=None):  # 接收消息时触发
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # 信息群发
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'system_message',
                'message': message
            }
        )

    # Receive message from room group
    async def system_message(self, data):
        message = data['message']

        # Send message to WebSocket单发消息
        await self.send(text_data=json.dumps({
            'message': message
        }, ensure_ascii=False))


def send_group_msg(group_name, message):
    # 从Channels的外部发送消息给Channel
    """
    from assets import consumers
    consumers.send_group_msg('ITNest', {'content': '这台机器硬盘故障了', 'level': 1})
    consumers.send_group_msg('ITNest', {'content': '正在安装系统', 'level': 2})
    :param group_name:
    :param message:
    :return:
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,  # 构造Channels组名称
        {
            "type": "system_message",
            "message": message,
        }
    )
