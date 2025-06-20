import json

from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import serializers

from farmbase.serializers import UserField
from playbook.models import ChecklistItem, Stage, LinkItem, CheckItem, Template, TemplateStage, \
    TemplateCheckGroup, TemplateCheckItem, TemplateLinkItem, TemplateRevisionHistory
from projects.serializers import ProjectStageSimpleSerializer


class TemplateField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = Template.objects.get(pk=value.pk)
        dict = {"id": value.pk, "template_type": proposal.template_type,
                "template_type_display": proposal.get_template_type_display(), "version": proposal.version,
                "status": proposal.status, "status_display": proposal.get_status_display(),
                "is_active": proposal.is_active
                }
        return dict


class TemplateStageField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = TemplateStage.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": proposal.name, "stage_code": proposal.stage_code}
        return dict


class TemplateRevisionHistoryField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = TemplateRevisionHistory.objects.get(pk=value.pk)
        dict = {"id": value.pk, "created_at": proposal.created_at.strftime(settings.DATETIME_FORMAT)}
        return dict


class TemplateCheckGroupField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = TemplateCheckGroup.objects.get(pk=value.pk)
        dict = {"id": value.pk, "description": proposal.description}
        return dict


class TemplateCheckItemField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = TemplateCheckItem.objects.get(pk=value.pk)
        dict = {"id": value.pk, "description": proposal.description, "period": proposal.period, "type": proposal.type,
                "period_display": proposal.get_period_display()}
        return dict


class LinkItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkItem
        fields = ('name', 'url', 'index')


class CheckItemSerializer(serializers.ModelSerializer):
    links = LinkItemSerializer(many=True, read_only=True)
    expected_date_base_display = serializers.SerializerMethodField()
    expected_weekday_display = serializers.SerializerMethodField()
    period_display = serializers.SerializerMethodField()

    stage_start_date = serializers.DateField()
    stage_end_date = serializers.DateField()

    class Meta:
        model = CheckItem
        fields = '__all__'

    def get_expected_date_base_display(self, obj):
        return obj.get_expected_date_base_display()

    def get_expected_weekday_display(self, obj):
        return obj.get_expected_weekday_display()

    def get_period_display(self, obj):
        return obj.get_period_display()


class CheckItemDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckItem
        fields = ['expected_date', 'expected_weekday']


class ChecklistItemSerializer(serializers.ModelSerializer):
    links = LinkItemSerializer(many=True, read_only=True)
    check_items = CheckItemSerializer(many=True, read_only=True)

    check_item_total = serializers.SerializerMethodField()
    finished_check_item_count = serializers.SerializerMethodField()
    undone_check_item_count = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistItem
        fields = (
            'id', 'checked', 'skipped', 'description', 'index', 'completed_at', 'links', 'check_items',
            'check_item_total',
            'finished_check_item_count', 'undone_check_item_count')

    def get_check_item_total(self, obj):
        return obj.check_items.count()

    def get_finished_check_item_count(self, obj):
        return obj.check_items.filter(completed_at__isnull=False).count()

    def get_undone_check_item_count(self, obj):
        undone_check_item_count = obj.check_items.filter(completed_at__isnull=True).count()
        if undone_check_item_count and obj.completed_at:
            obj.checked = False
            obj.skipped = False
            obj.completed_at = None
            obj.save()
        return undone_check_item_count


class StageSerializer(serializers.ModelSerializer):
    check_groups = ChecklistItemSerializer(many=True, read_only=True)
    check_group_total = serializers.SerializerMethodField()
    finished_check_group_count = serializers.SerializerMethodField()

    stage_start_date = serializers.DateField()
    stage_end_date = serializers.DateField()

    # project_stage = ProjectStageSimpleSerializer(read_only=True)

    class Meta:
        model = Stage
        fields = ('id', 'name', 'stage_code',
                  'status_index', 'index', 'check_groups', 'check_group_total',
                  'finished_check_group_count', 'member_type', 'stage_start_date', 'stage_end_date',
                  'is_previous_stage', 'is_current_stage', 'is_next_stage')

    def get_check_group_total(self, obj):
        return obj.check_groups.count()

    def get_finished_check_group_count(self, obj):
        return obj.check_groups.filter(completed_at__isnull=False).count()


class TemplateLinkItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateLinkItem
        fields = '__all__'


class TemplateCheckItemSerializer(serializers.ModelSerializer):
    period_display = serializers.SerializerMethodField()
    expected_date_base_display = serializers.SerializerMethodField()
    expected_weekday_display = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCheckItem
        fields = '__all__'

    def get_period_display(self, obj):
        return obj.get_period_display()

    def get_expected_date_base_display(self, obj):
        return obj.get_expected_date_base_display()

    def get_expected_weekday_display(self, obj):
        return obj.get_expected_weekday_display()

    def get_links(self, obj):
        return TemplateLinkItemSerializer(obj.links.order_by('index'), many=True).data


class TemplateCheckGroupSerializer(serializers.ModelSerializer):
    check_items = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCheckGroup
        fields = '__all__'

    def get_check_items(self, obj):
        return TemplateCheckItemSerializer(obj.check_items.order_by('index'), many=True).data


class TemplateStageSerializer(serializers.ModelSerializer):
    check_groups = serializers.SerializerMethodField()

    class Meta:
        model = TemplateStage
        fields = '__all__'

    def get_check_groups(self, obj):
        return TemplateCheckGroupSerializer(obj.check_groups.order_by('index'), many=True).data


class TemplateListSerializer(serializers.ModelSerializer):
    template_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    member_type_display = serializers.SerializerMethodField()
    creator = UserField(many=False, queryset=User.objects.all(), required=False)
    last_operator = UserField(many=False, queryset=User.objects.all(), required=False)
    publisher = UserField(many=False, queryset=User.objects.all(), required=False)

    class Meta:
        model = Template
        fields = '__all__'

    def get_template_type_display(self, obj):
        return obj.get_template_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_member_type_display(self, obj):
        return obj.get_member_type_display()


class TemplateSerializer(serializers.ModelSerializer):
    template_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    member_type_display = serializers.SerializerMethodField()
    creator = UserField(many=False, queryset=User.objects.all(), required=False)
    last_operator = UserField(many=False, queryset=User.objects.all(), required=False)
    publisher = UserField(many=False, queryset=User.objects.all(), required=False)

    revision_history = TemplateRevisionHistoryField(many=False, read_only=True)

    stages = serializers.SerializerMethodField()

    class Meta:
        model = Template
        fields = '__all__'

    def get_template_type_display(self, obj):
        return obj.get_template_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_member_type_display(self, obj):
        return obj.get_member_type_display()

    def get_stages(self, obj):
        return TemplateStageSerializer(obj.stages.order_by('index'), many=True).data


class TemplateCheckGroupEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateCheckGroup
        fields = ['description']


class TemplateCheckGroupWithStageSerializer(serializers.ModelSerializer):
    template_stage = TemplateStageField(many=False, queryset=TemplateStage.objects.all(), required=False)

    class Meta:
        model = TemplateCheckGroup
        fields = '__all__'


class TemplateCheckItemWithGroupSerializer(serializers.ModelSerializer):
    period_display = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()
    template_check_group = TemplateCheckGroupWithStageSerializer(many=False, read_only=True)

    class Meta:
        model = TemplateCheckItem
        fields = '__all__'

    def get_period_display(self, obj):
        return obj.get_period_display()

    def get_links(self, obj):
        return TemplateLinkItemSerializer(obj.links.order_by('index'), many=True).data


class TemplateCheckGroupEditableFieldSerializer(serializers.ModelSerializer):
    template_stage = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCheckGroup
        fields = ['description', "template_stage"]

    def get_template_stage(self, obj):
        return {"name": obj.template_stage.name}


class TemplateCheckItemEditableFieldSerializer(serializers.ModelSerializer):
    template_check_group = TemplateCheckGroupEditableFieldSerializer(many=False, read_only=True)
    period_display = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCheckItem
        fields = ["type", "period", "period_display", 'description', "template_check_group", "links", "notice"]

    def get_period_display(self, obj):
        return obj.get_period_display()

    def get_links(self, obj):
        data = []
        for link in obj.links.order_by('index'):
            data.append({"name": link.name, "url": link.url})
        return data


class TemplateRevisionHistorySerializer(serializers.ModelSerializer):
    playbook_template = TemplateField(many=False, queryset=Template.objects.all(), required=False)
    content_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TemplateRevisionHistory
        fields = '__all__'

    def get_content_data(self, obj):
        if obj.content_data:
            return json.loads(obj.content_data, encoding='utf-8')
