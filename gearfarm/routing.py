# 【channels】（第2步）设置默认路由在项目创建routing.py文件
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
from django.urls import path

from notifications import consumers

application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)
    'websocket': AuthMiddlewareStack(  # 使用Session中间件，可以请求中session的值
        URLRouter([
            path('ws/<group_name>/', consumers.AsyncConsumer),
        ])
    ),
})
