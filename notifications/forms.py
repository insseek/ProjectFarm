from django import forms
from django.contrib.auth.models import User, Group

from notifications.models import Notification


class NotificationPostForm(forms.Form):
    users = forms.ModelMultipleChoiceField(queryset=User.objects.filter(is_active=True), required=False)
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)
    priority = forms.ChoiceField(choices=Notification.PRIORITY_CHOICES, required=False)
    need_alert = forms.BooleanField(required=False)
    url = forms.URLField(required=False)
    content = forms.CharField(widget=forms.Textarea(attrs={'cols': '40', 'rows': '3'}))
