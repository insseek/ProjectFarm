import json

from django.conf import settings
from rest_framework import serializers

from developers.models import Developer
from files.serializers import FileField, File
from finance.models import JobPayment, ProjectPayment, ProjectPaymentStage, JobContract
from farmbase.serializers import UserField, User, UserBasicSerializer
from projects.models import Project, JobPosition
from projects.serializers import JobSerializer, JobField, JobWithProjectSerializer
from projects.utils.common_utils import get_project_members_dict, get_user_data


class ProjectVerySimpleSerializer(serializers.ModelSerializer):
    manager = UserField(many=False, queryset=User.objects.all(), required=False)

    class Meta:
        model = Project
        fields = ('id', 'name', 'manager')


class DeveloperField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        developer = Developer.objects.get(pk=value.pk)
        avatar = None
        if developer.avatar:
            avatar = developer.avatar.url
        dict = {"id": value.pk, "name": developer.name, 'username': developer.name, 'phone': developer.phone,
                'avatar': avatar, 'avatar_url': avatar, "is_real_name_auth":developer.is_real_name_auth}
        return dict


class ProjectField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        project = Project.objects.get(pk=value.pk)
        return ProjectSimpleSerializer(project).data


class ProjectSimpleSerializer(serializers.ModelSerializer):
    manager = UserField(many=False, read_only=True)
    members_dict = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'done_at', 'created_at', 'manager', 'members_dict')

    def get_members_dict(self, obj):
        return get_project_members_dict(obj)


# 创建打款项的字段
class JobPaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPayment
        fields = ['position', 'developer', 'job_contract', 'name', 'bank_info', 'amount', 'expected_at', 'remarks',
                  'submitter',
                  'payee_name', 'payee_id_card_number', 'payee_phone', 'payee_opening_bank', 'payee_account',
                  'payment_reason']


class JobPaymentEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPayment
        fields = ['name', 'bank_info', 'amount', 'expected_at', 'remarks', 'payee_name', 'payee_id_card_number',
                  'payee_phone', 'payee_opening_bank', 'payee_account', 'payment_reason']


class JobPaymentWithPositionSerializer(serializers.ModelSerializer):
    position = JobSerializer(many=False, read_only=True)

    class Meta:
        model = JobPayment
        fields = '__all__'


# 项目收款

class ProjectPaymentStageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPaymentStage
        fields = ['project_payment', 'receivable_amount', 'expected_date', 'index']


class ProjectPaymentStageEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPaymentStage
        fields = ['receivable_amount', 'expected_date', 'index']


class ProjectPaymentStageExpectedDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPaymentStage
        fields = ['expected_date', ]


class ProjectPaymentStageReceiptedSerializer(serializers.ModelSerializer):
    receipted_amount = serializers.FloatField()
    receipted_date = serializers.DateField()
    invoice = serializers.CharField()

    class Meta:
        model = ProjectPaymentStage
        fields = ['receipted_amount', 'receipted_date', 'invoice']


class ProjectPaymentStageSerializer(serializers.ModelSerializer):
    invoice_display = serializers.CharField(read_only=True)

    class Meta:
        model = ProjectPaymentStage
        fields = '__all__'


class ProjectPaymentSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    paid_total_amount = serializers.FloatField(read_only=True)
    stages = serializers.SerializerMethodField(read_only=True)
    invoice_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    termination_reason_display = serializers.CharField(read_only=True)
    paid_stage_count = serializers.IntegerField(read_only=True)
    total_stage_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProjectPayment
        fields = '__all__'

    def get_stages(self, obj):
        stages = obj.stages.order_by('index')
        data = ProjectPaymentStageSerializer(stages, many=True).data
        return data


class ProjectPaymentCreateSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    contract_name = serializers.CharField()
    capital_account = serializers.CharField()
    total_amount = serializers.FloatField()
    invoice = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = ProjectPayment
        fields = ['project', 'contract_name', 'capital_account', 'total_amount', 'invoice', 'remarks']


class ProjectPaymentEditSerializer(serializers.ModelSerializer):
    contract_name = serializers.CharField()
    capital_account = serializers.CharField()
    total_amount = serializers.FloatField()
    invoice = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = ProjectPayment
        fields = ['contract_name', 'capital_account', 'total_amount', 'invoice', 'remarks']


class ProjectWithPaymentSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    manager = UserField(many=False, read_only=True)
    payments = serializers.SerializerMethodField(read_only=True)
    max_payment_stage_count = serializers.SerializerMethodField(read_only=True)
    members_dict = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'created_at', 'done_at', 'status_display', 'status', 'manager', 'product_manager', 'payments',
            'max_payment_stage_count', 'members_dict'
        )

    def get_payments(self, obj):
        payments = obj.project_payments.all().order_by('created_at')
        data = ProjectPaymentSerializer(payments, many=True).data
        return data

    def get_max_payment_stage_count(self, obj):
        payments = obj.project_payments.all()
        stage_count_list = [payment.stages.count() for payment in payments]
        if stage_count_list:
            return max(stage_count_list)

    def get_members_dict(self, obj):
        return get_project_members_dict(obj)


class JobRegularContractCreateSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, queryset=Developer.objects.all())
    principal = UserField(many=False, queryset=User.objects.all())
    creator = UserField(many=False, queryset=User.objects.all())

    class Meta:
        model = JobContract
        fields = ['contract_name', 'contract_category', 'developer', 'principal', 'creator', 'develop_date_start',
                  'develop_date_end', 'contract_money',
                  'pay_way', 'remit_way', 'project_results_show']


class JobContractCreateSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, queryset=Developer.objects.all())
    job_position = JobField(queryset=JobPosition.objects.all())
    develop_function_declaration = FileField(queryset=File.objects.filter(is_deleted=False))

    class Meta:
        model = JobContract
        fields = '__all__'


class JobDesignContractCreateSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, queryset=Developer.objects.all())
    job_position = JobField(queryset=JobPosition.objects.all())
    delivery_list = FileField(queryset=File.objects.filter(is_deleted=False))

    class Meta:
        model = JobContract
        exclude = ['develop_sprint']


class JobContractEditSerializer(serializers.ModelSerializer):
    develop_function_declaration = FileField(queryset=File.objects.filter(is_deleted=False))

    class Meta:
        model = JobContract
        fields = ['contract_name', 'contract_category', 'develop_date_start', 'develop_date_end', 'develop_days',
                  'contract_money',
                  'develop_sprint', 'remit_way', 'project_results_show', 'maintain_period', 'remarks',
                  'develop_function_declaration']


class JobDesignContractEditSerializer(serializers.ModelSerializer):
    delivery_list = FileField(queryset=File.objects.filter(is_deleted=False))

    class Meta:
        model = JobContract
        fields = ['contract_name', 'develop_date_start', 'develop_date_end', 'develop_days', 'contract_money',
                  'remit_way', 'maintain_period', 'remarks', 'pay_way', 'delivery_list', 'style_confirm',
                  'global_design', 'walk_through']


class JobRegularContractRedactSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, queryset=Developer.objects.all())
    principal = UserField(many=False, queryset=User.objects.all())

    class Meta:
        model = JobContract
        fields = ['contract_name', 'contract_category', 'developer', 'principal', 'develop_date_start',
                  'develop_date_end', 'contract_money',
                  'pay_way', 'remit_way', 'project_results_show',
                  'name', 'id_card_number', 'email', 'phone',
                  'front_side_of_id_card', 'address',
                  'back_side_of_id_card', 'payee_name', 'payee_id_card_number', 'payee_phone', 'payee_opening_bank',
                  'payee_account']


class JobContractRedactSerializer(serializers.ModelSerializer):
    front_side_of_id_card = serializers.FileField(required=False)
    back_side_of_id_card = serializers.FileField(required=False)

    class Meta:
        model = JobContract
        fields = ['name', 'id_card_number', 'email', 'phone', 'front_side_of_id_card', 'address',
                  'back_side_of_id_card', 'payee_name', 'payee_id_card_number', 'payee_phone', 'payee_opening_bank',
                  'payee_account']


class DeveloperContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        fields = ('name', 'id_card_number', 'email', 'phone', 'front_side_of_id_card', 'address',
                  'back_side_of_id_card', 'payee_name', 'payee_id_card_number', 'payee_phone', 'payee_opening_bank',
                  'payee_account')


class JobContractRegularListSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, read_only=True)
    principal = UserField(many=False, read_only=True)
    creator = UserField(many=False, read_only=True)
    develop_info = serializers.SerializerMethodField()
    remit_way = serializers.SerializerMethodField()
    project_results_show = serializers.SerializerMethodField()
    contract_type = serializers.CharField()
    is_perfect = serializers.BooleanField(read_only=True)

    payments_statistics = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()

    class Meta:
        model = JobContract
        fields = '__all__'

    def get_payments(self, obj):
        payments = obj.payments.all().order_by('created_at')
        if payments:
            return JobPaymentListSerializer(payments, many=True).data
        return []

    def get_remit_way(self, obj):
        return json.loads(obj.remit_way) if obj.remit_way else ''

    def get_project_results_show(self, obj):
        return json.loads(obj.project_results_show) if obj.project_results_show else []

    def get_payments_statistics(self, obj):
        return obj.payments_statistics

    def get_develop_info(self, obj):
        if obj.developer:
            return DeveloperContractSerializer(obj.developer).data


# 工程师合同列表页
class JobContractListSerializer(serializers.ModelSerializer):
    job_position = JobWithProjectSerializer(many=False, read_only=True)
    project = ProjectVerySimpleSerializer(many=False, read_only=True)
    developer = DeveloperField(many=False, read_only=True)
    develop_info = serializers.SerializerMethodField()
    remit_way = serializers.SerializerMethodField()
    project_results_show = serializers.SerializerMethodField()

    develop_function_declaration = FileField(read_only=True)
    delivery_list = FileField(read_only=True)
    is_perfect = serializers.BooleanField(read_only=True)
    contract_type = serializers.CharField()

    class Meta:
        model = JobContract
        fields = '__all__'

    def get_develop_info(self, obj):
        if obj.developer:
            return DeveloperContractSerializer(obj.developer).data

    def get_remit_way(self, obj):
        return json.loads(obj.remit_way) if obj.remit_way else ''

    def get_project_results_show(self, obj):
        return json.loads(obj.project_results_show) if obj.project_results_show else []


class JobContractDetailSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, read_only=True)
    job_position = JobWithProjectSerializer(many=False, read_only=True)
    develop_info = serializers.SerializerMethodField()
    remit_way = serializers.SerializerMethodField()
    project_results_show = serializers.SerializerMethodField()
    develop_function_declaration = FileField(read_only=True)
    delivery_list = FileField(read_only=True)

    payments_statistics = serializers.SerializerMethodField()
    is_perfect = serializers.BooleanField(read_only=True)
    contract_type = serializers.CharField()

    class Meta:
        model = JobContract
        fields = '__all__'

    def get_develop_info(self, obj):
        if obj.developer:
            return DeveloperContractSerializer(obj.developer).data

    def get_remit_way(self, obj):
        return json.loads(obj.remit_way) if obj.remit_way else ''

    def get_project_results_show(self, obj):
        return json.loads(obj.project_results_show) if obj.project_results_show else []

    def get_payments_statistics(self, obj):
        return obj.payments_statistics


class JobContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobContract
        fields = '__all__'


class JobContractStatisticSerializer(serializers.ModelSerializer):
    payments_statistics = serializers.SerializerMethodField()
    remit_way = serializers.SerializerMethodField()
    project_results_show = serializers.SerializerMethodField()

    class Meta:
        model = JobContract
        fields = '__all__'

    def get_payments_statistics(self, obj):
        return obj.payments_statistics

    def get_remit_way(self, obj):
        return json.loads(obj.remit_way) if obj.remit_way else ''

    def get_project_results_show(self, obj):
        return json.loads(obj.project_results_show) if obj.project_results_show else []


class JobPaymentBoardSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(many=False, read_only=True)
    position = JobField(many=False, read_only=True)
    developer = DeveloperField(many=False, read_only=True)
    submitter = UserField(many=False, read_only=True)
    manager = UserBasicSerializer(many=False, read_only=True)

    status_display = serializers.CharField()
    comments_count = serializers.IntegerField()
    job_contract = JobContractStatisticSerializer(many=False, read_only=True)

    class Meta:
        model = JobPayment
        fields = '__all__'


# 详情 包含了 合同的信息
class JobPaymentRetrieveSerializer(serializers.ModelSerializer):
    job_contract = JobContractStatisticSerializer(many=False, read_only=True)
    position = JobField(many=False, read_only=True)
    developer = DeveloperField(many=False, read_only=True)
    comments_count = serializers.IntegerField()

    class Meta:
        model = JobPayment
        fields = '__all__'


class JobPaymentListSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, read_only=True)
    comments_count = serializers.IntegerField()
    status_display = serializers.CharField()

    class Meta:
        model = JobPayment
        fields = ['id', 'amount', 'expected_at', 'status', 'status_display', 'comments_count', 'payment_reason',
                  'remarks', 'developer']
