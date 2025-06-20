from datetime import datetime
import json

from django.conf import settings
from rest_framework import serializers

from developers.models import Developer
from projects.models import JobPosition, Project
from finance.models import JobPayment, ProjectPayment, ProjectPaymentStage, JobContract


class JobExportSerializer(serializers.ModelSerializer):
    developer_name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    project_status_display = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()

    days = serializers.SerializerMethodField()

    total_amount = serializers.FloatField(read_only=True)
    paid_payment_amount = serializers.FloatField(read_only=True)
    last_paid_payment_amount = serializers.FloatField(read_only=True)
    last_paid_payment_date = serializers.DateField(read_only=True, allow_null=True)

    created_at = serializers.DateTimeField(format=settings.DATE_FORMAT)

    class Meta:
        model = JobPosition
        fields = ['developer_name', 'project_name', 'project_status_display', 'manager_name', 'role_name', 'created_at',
                  'days', 'total_amount',
                  'paid_payment_amount', 'last_paid_payment_amount', 'last_paid_payment_date']

    def get_developer_name(self, obj):
        return obj.developer.name

    def get_project_name(self, obj):
        return obj.project.name

    def get_project_status_display(self, obj):
        return obj.project.status_display

    def get_manager_name(self, obj):
        if obj.project.manager:
            return obj.project.manager.username

    def get_role_name(self, obj):
        return obj.role.name

    def get_days(self, obj):
        days = (datetime.now() - obj.created_at).days
        return str(days) + '天'


class JobUnevaluatedExportSerializer(serializers.ModelSerializer):
    project_name = serializers.SerializerMethodField()
    project_done_at = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()

    developer_name = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    developer_is_active = serializers.SerializerMethodField()

    total_amount = serializers.FloatField(read_only=True)

    class Meta:
        model = JobPosition
        fields = ['project_name', 'project_done_at', 'manager_name', 'developer_name', 'role_name',
                  'developer_is_active', 'total_amount']

    def get_project_name(self, obj):
        return obj.project.name

    def get_project_done_at(self, obj):
        return obj.project.done_at.strftime(settings.DATE_FORMAT) if obj.project.done_at else None

    def get_manager_name(self, obj):
        if obj.project.manager:
            return obj.project.manager.username

    def get_developer_name(self, obj):
        if obj.developer:
            return obj.developer.name

    def get_role_name(self, obj):
        return obj.role.name

    def get_developer_is_active(self, obj):
        if obj.developer:
            return obj.developer.is_active


# 工程师打款导出
class JobPaymentExportSerializer(serializers.ModelSerializer):
    contract_name = serializers.SerializerMethodField()

    class Meta:
        model = JobPayment
        fields = ['id', 'expected_at', 'completed_at', 'amount', 'status_display', 'contract_name', 'payee_name',
                  'payee_id_card_number', 'payee_phone', 'payee_opening_bank', 'payee_account', 'remarks']

    def get_contract_name(self, obj):
        if obj.job_contract:
            return obj.job_contract.contract_name
        return "无合同 {}".format(obj.payment_reason or '')


class JobPositionWithJobPaymentExportSerializer(serializers.ModelSerializer):
    role_name = serializers.SerializerMethodField()
    developer_name = serializers.SerializerMethodField()
    total_amount = serializers.FloatField()
    payments = serializers.SerializerMethodField()

    class Meta:
        model = JobPosition
        fields = ['role_name', 'developer_name', 'paid_payment_amount', 'total_amount', 'payments']

    def get_role_name(self, obj):
        if obj.role:
            if obj.role_remarks:
                return '{role}({remark})'.format(role=obj.role.name, remark=obj.role_remarks)
            return obj.role.name

    def get_developer_name(self, obj):
        if obj.developer:
            return obj.developer.name

    def get_payments(self, obj):
        payments = obj.payments.exclude(status=0).order_by('created_at')
        return JobPaymentExportSerializer(payments, many=True).data


class ProjectWithJobPositionExportSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    manager_username = serializers.SerializerMethodField()
    job_positions = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format='%Y.%m.%d')

    class Meta:
        model = Project
        fields = ['name', 'manager_username', 'status_display', 'created_at', 'done_at', 'job_positions']

    def get_name(self, obj):
        return '【{id}】{name}'.format(id=obj.id, name=obj.name)

    def get_manager_username(self, obj):
        if obj.manager:
            return obj.manager.username

    def get_job_positions(self, obj):
        job_positions = obj.job_positions.order_by('created_at')
        return JobPositionWithJobPaymentExportSerializer(job_positions, many=True).data


class DeveloperWithRegularExportSerializer(serializers.ModelSerializer):
    regular_contracts = serializers.SerializerMethodField()

    class Meta:
        model = Developer
        fields = ['id', 'name', "regular_contracts"]

    def get_regular_contracts(self, obj):
        job_positions = obj.job_contracts.filter(contract_category='regular', status='signed')
        return JobContractWithJobPaymentExportSerializer(job_positions, many=True).data


class JobContractWithJobPaymentExportSerializer(serializers.ModelSerializer):
    principal_name = serializers.SerializerMethodField()
    developer_name = serializers.SerializerMethodField()
    total_amount = serializers.FloatField()
    payments = serializers.SerializerMethodField()
    signed_at = serializers.DateTimeField(format='%Y.%m.%d')

    class Meta:
        model = JobContract
        fields = ['contract_name', 'developer_name', 'principal_name', 'paid_payment_amount', 'total_amount',
                  'payments', 'signed_at']

    def get_principal_name(self, obj):
        if obj.principal:
            return obj.principal.username

    def get_payments(self, obj):
        payments = obj.payments.exclude(status=0).order_by('created_at')
        return JobPaymentExportSerializer(payments, many=True).data

    def get_developer_name(self, obj):
        if obj.developer:
            return obj.developer.name


class ProjectExportSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    manager_username = serializers.SerializerMethodField()
    bd_username = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['name', 'manager_username', 'created_at', 'done_at', 'bd_username']

    def get_name(self, obj):
        return '【{id}】{name}'.format(id=obj.id, name=obj.name)

    def get_manager_username(self, obj):
        if obj.manager:
            return obj.manager.username

    def get_bd_username(self, obj):
        if obj.bd:
            return obj.bd.username


class ProjectPaymentStageSerializer(serializers.ModelSerializer):
    invoice_display = serializers.CharField(read_only=True)

    class Meta:
        model = ProjectPaymentStage
        fields = '__all__'


class ProjectPaymentExportSerializer(serializers.ModelSerializer):
    project_name = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField()
    invoice_display = serializers.CharField()
    stages = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProjectPayment
        fields = '__all__'

    def get_project_name(self, obj):
        return obj.project.name

    def get_stages(self, obj):
        stages = obj.stages.order_by('index')
        data = ProjectPaymentStageSerializer(stages, many=True).data
        return data
