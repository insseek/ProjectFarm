from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db.models import NOT_PROVIDED, DateTimeField, Model, DateField, ManyToManyField
from django.utils import timezone
from django.utils.encoding import smart_text

import multiselectfield


def get_field_value(obj, field):
    if isinstance(field, ManyToManyField):
        field_queryset = getattr(obj, field.name).all()
        value_list = []
        try:
            value_list = sorted([str(i) for i in field_queryset])
        except:
            pass
        value = ','.join(value_list)
    elif isinstance(field, multiselectfield.db.fields.MultiSelectField):
        choices_dict = dict(field.choices)
        value = getattr(obj, field.name, None)
        if isinstance(value, multiselectfield.db.fields.MSFList):
            value_set = set(value)
        elif value and isinstance(value, set):
            value_set = value
        else:
            value_set = set()
        value_list = sorted([str(choices_dict[value]) for value in value_set if value in choices_dict])
        value = ','.join(value_list)
    elif isinstance(field, DateTimeField):
        try:
            value = field.to_python(getattr(obj, field.name, None))
            if value is not None and settings.USE_TZ:
                value = timezone.make_naive(value, timezone=timezone.utc)
        except ObjectDoesNotExist:
            value = field.default if field.default is not NOT_PROVIDED else None
        if value:
            value = value.strftime(settings.DATETIME_FORMAT)
    elif isinstance(field, DateField):
        try:
            value = field.to_python(getattr(obj, field.name, None))
            if value is not None and settings.USE_TZ:
                value = timezone.make_naive(value, timezone=timezone.utc)
        except ObjectDoesNotExist:
            value = field.default if field.default is not NOT_PROVIDED else None
        if value:
            value = value.strftime(settings.DATE_FORMAT)
    else:
        try:
            value = smart_text(getattr(obj, field.name, None))
        except (ObjectDoesNotExist, AttributeError):
            value = field.default if field.default is not NOT_PROVIDED else None
        if hasattr(field, 'choices') and len(field.choices) > 0:
            for name, verbose_name in field.choices:
                if str(value) == str(name):
                    value = verbose_name
                    break
    return value
