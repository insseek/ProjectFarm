from notifications.consumers import send_group_msg


class ChannelsPusher(object):
    def trigger(self, channel, event_name, data, ):
        message = {'event_name': event_name, 'data': data}
        send_group_msg(channel, message)


notification_pusher = ChannelsPusher()
