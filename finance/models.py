import uuid

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Sum, IntegerField, When, Case, Q
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.utils import timezone

from files.models import File
from logs.models import Log
from tasks.models import Task


# 工程师职位合同
class JobContract(models.Model):
    STATUS = (
        ("uncommitted", "未提交"),
        ("un_generate", "待生成"),
        ("rejected", "已驳回"),
        ("waiting", "待签约"),
        ("signed", "已签约"),
        ("closed", "已关闭")
    )
    PAY_WAY = (
        ('one_off', '一次性支付'),
        ('installments', '分阶段支付')
    )
    CONTRACT_CATEGORY_CHOICES = (
        ('project', '项目合同'),
        ('regular', '固定合同'),
    )

    PAY_STATUS = (
        ("ongoing", "进行中"),
        ("completed", "正常完成"),
        ("terminated", "异常终止")
    )

    TERMINATION_REASON = (
        ('terminated', '合同终止'),
        ('clerical_error', '填写错误')
    )

    def generate_filename(self, filename):
        url = "developers-{}-{}-{}".format(self.name, str(uuid.uuid4())[:6], filename)
        return url

    status = models.CharField(verbose_name='合同状态', choices=STATUS, default='uncommitted', max_length=20)
    pay_status = models.CharField(verbose_name="打款状态", max_length=50, choices=PAY_STATUS, blank=True, null=True)
    terminated_remarks = models.TextField(verbose_name='终止备注', blank=True, null=True)
    terminated_reason = models.CharField(verbose_name='终止原因', blank=True, null=True, max_length=32,
                                         choices=TERMINATION_REASON)
    completed_at = models.DateTimeField(verbose_name='完成时间', null=True, blank=True)

    principal = models.ForeignKey(User, verbose_name="负责人", related_name='principal_job_contracts', blank=True,
                                  null=True,
                                  on_delete=models.SET_NULL)
    creator = models.ForeignKey(User, verbose_name='创建人', related_name='creator_job_contracts',
                                on_delete=models.SET_NULL,
                                null=True, blank=True)
    contract_category = models.CharField(verbose_name='合同类型', choices=CONTRACT_CATEGORY_CHOICES,
                                         default='project', max_length=25)

    contract_name = models.CharField(verbose_name='合同名字', max_length=200)
    develop_date_start = models.DateField(verbose_name='开发周期开始日期')
    develop_date_end = models.DateField(verbose_name='开发周期结束日期')
    develop_days = models.IntegerField(verbose_name='开发天数', null=True, blank=True)
    contract_money = models.IntegerField(verbose_name='合同金额')
    develop_sprint = models.IntegerField(verbose_name='开发sprint数量', null=True, blank=True)

    pay_way = models.CharField(verbose_name='支付方式', choices=PAY_WAY, default='installments', max_length=20)
    remit_way = models.TextField(verbose_name='打款方式', null=True, blank=True)
    # 固定工程师打款示例
    # {"timedelta_weeks":2,  "amount":9000}
    # 分阶段打款示例
    # "remit_way": [
    #     {
    #         "name": "第一个开发阶段结束并审核通过",
    #         "proportion": 30,
    #         "money": 90
    #     },
    #     {
    #         "name": "开发完成且全部代码审核通过",
    #         "proportion": 30,
    #         "money": 90
    #     },
    #     {
    #         "name": "项目验收通过",
    #         "proportion": 40,
    #         "money": 120
    #     }
    # ],
    project_results_show = models.TextField(verbose_name='项目成果交付')
    maintain_period = models.IntegerField(verbose_name='工程师维护周期', default=6)
    develop_function_declaration = models.ForeignKey(File, verbose_name='开发功能说明', null=True, blank=True,
                                                     on_delete=models.SET_NULL, related_name='common_contracts')
    # 设计的字段
    delivery_list = models.ForeignKey(File, verbose_name='交付清单', null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='design_contracts')
    style_confirm = models.DateField(verbose_name='风格确认时间', null=True, blank=True)
    global_design = models.DateField(verbose_name='整体设计时间', null=True, blank=True)
    walk_through = models.DateField(verbose_name='设计走查', null=True, blank=True)
    # 设计的字段

    remarks = models.TextField(verbose_name='备注', null=True, blank=True)
    developer = models.ForeignKey('developers.Developer', related_name='job_contracts', on_delete=models.CASCADE,
                                  null=True, blank=True)
    job_position = models.ForeignKey('projects.JobPosition', related_name='job_contracts', on_delete=models.CASCADE,
                                     null=True, blank=True)

    close_reason = models.TextField(verbose_name='关闭原因', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    modified_at = models.DateTimeField(verbose_name="修改时间", auto_now=True)

    committed_at = models.DateTimeField(verbose_name='提交时间', null=True, blank=True)
    generate_at = models.DateTimeField(verbose_name='生成时间', null=True, blank=True)
    # sign_date = models.DateTimeField(verbose_name='签约日期', null=True, blank=True)
    # close_date = models.DateTimeField(verbose_name='关闭日期', null=True, blank=True)
    signed_at = models.DateTimeField(verbose_name='签约时间', null=True, blank=True)
    closed_at = models.DateTimeField(verbose_name='关闭时间', null=True, blank=True)
    is_null_contract = models.BooleanField(verbose_name='是否是空合同', default=False)

    # 工程师信息
    name = models.CharField(max_length=50, verbose_name='名称', null=True, blank=True)
    fadada = models.CharField(max_length=30, verbose_name='法大大', blank=True, null=True)
    id_card_number = models.CharField(max_length=30, verbose_name='身份证号码', blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name='手机号', blank=True, null=True)
    address = models.CharField(max_length=100, verbose_name='地址', null=True, blank=True)
    is_confidentiality_agreement = models.BooleanField(verbose_name='是否有保密协议', default=True)
    front_side_of_id_card = models.ImageField(upload_to=generate_filename, verbose_name='身份证正面照', null=True,
                                              blank=True)
    back_side_of_id_card = models.ImageField(upload_to=generate_filename, verbose_name='身份证反面照', null=True,
                                             blank=True)
    is_esign_contract = models.BooleanField(verbose_name='是否是E签宝合同', default=True)
    flow_id = models.CharField(verbose_name='合同签署流程id', max_length=100, null=True, blank=True)
    secret_flow_id = models.CharField(verbose_name='保密协议签署流程id', max_length=100, null=True, blank=True)
    file_id = models.CharField(verbose_name='合同文件id', max_length=100, null=True, blank=True)
    secret_file_id = models.CharField(verbose_name='保密协议文件id', max_length=100, null=True, blank=True)
    is_sign_contract = models.BooleanField(verbose_name='是否已签署工程师合同', default=False)
    is_sign_secret = models.BooleanField(verbose_name='是否已签署保密协议', default=False)
    contract_sign_link = models.TextField(verbose_name='主合同签署链接', null=True, blank=True)
    secret_sign_link = models.TextField(verbose_name='保密协议签署链接', null=True, blank=True)

    # 收款信息
    payee_name = models.CharField(max_length=50, verbose_name='收款人户名', blank=True, null=True)
    payee_id_card_number = models.CharField(max_length=30, verbose_name='收款人身份证号码', blank=True, null=True)
    payee_phone = models.CharField(max_length=20, verbose_name='收款人手机号', blank=True, null=True)
    payee_opening_bank = models.TextField(verbose_name='收款人开户行', blank=True, null=True)
    payee_account = models.CharField(verbose_name='收款人收款账号', null=True, blank=True, max_length=50)

    def __str__(self):
        return '%s' % self.contract_name

    class Meta:
        verbose_name = '工程师合同'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        self.rebuild_pay_status()
        super(JobContract, self).save(*args, **kwargs)

    def rebuild_pay_status(self):
        if self.status == 'signed':
            if self.is_fully_paid:
                self.pay_status = 'completed'
                self.completed_at = timezone.now()
            elif self.pay_status == 'completed':
                self.pay_status = 'ongoing'
            elif not self.pay_status:
                self.pay_status = 'ongoing'

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def pay_status_display(self):
        return self.get_pay_status_display()

    @property
    def manager(self):
        if self.principal:
            return self.principal
        if self.job_position:
            return self.job_position.project.manager

    @property
    def project(self):
        if self.job_position:
            return self.job_position.project

    @classmethod
    def signed_regular_contracts(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(contract_category='regular', status='signed')

    @classmethod
    def valid_project_contracts(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(contract_category='project').exclude(is_null_contract=True).exclude(
            status__in=['uncommitted', 'rejected'])

    @classmethod
    def valid_regular_contracts(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(contract_category='regular').exclude(status__in=['uncommitted', 'rejected'])

    @classmethod
    def my_regular_contracts(cls, user, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        queryset = queryset.filter(contract_category='regular').filter(
            Q(creator_id=user.id) | Q(principal_id=user.id)).exclude(status__in=['uncommitted', 'rejected'])
        return queryset

    @property
    def is_perfect(self):
        fields = ('name', 'fadada', 'id_card_number', 'email', 'phone', 'front_side_of_id_card',
                  'back_side_of_id_card', 'payee_name', 'payee_id_card_number', 'payee_phone', 'payee_opening_bank',
                  'payee_account')
        for i in fields:
            if not getattr(self, i, None):
                return False
        return True

    @property
    def total_amount(self):
        return self.contract_money

    @property
    def is_fully_paid(self):
        if self.contract_money:
            return int(self.contract_money) == int(self.paid_payment_amount)
        return True

    # 已完成
    @property
    def paid_payment_amount(self):
        payments = self.payments.filter(status=2)
        if payments.exists():
            return sum(payments.values_list('amount', flat=True))
        return 0

    # 进行中的
    @property
    def ongoing_payment_amount(self):
        paid_amount = self.payments.filter(status=1)
        if paid_amount.exists():
            return sum(paid_amount.values_list('amount', flat=True))
        return 0

    # 记录的
    @property
    def recorded_payment_amount(self):
        processing_payments = self.payments.filter(status=0)
        if processing_payments.exists():
            return sum(processing_payments.values_list('amount', flat=True))
        return 0

    @property
    def remaining_payment_amount(self):
        return self.total_amount - self.normal_payment_amount

    @property
    def remaining_include_recorded_payment_amount(self):
        return self.total_amount - self.paid_payment_amount - self.ongoing_payment_amount

    # 非异常的
    @property
    def normal_payment_amount(self):
        payments = self.payments.exclude(status=3)
        if payments.exists():
            return sum(payments.values_list('amount', flat=True))
        return 0

    @property
    def last_paid_payment_amount(self):
        if self.last_paid_payment:
            return self.last_paid_payment.amount

    @property
    def last_paid_payment_date(self):
        if self.last_paid_payment:
            return self.last_paid_payment.completed_at

    @property
    def last_paid_payment(self):
        paid_payment = self.payments.filter(status=2).order_by('-completed_at').first()
        return paid_payment

    @property
    def payments_statistics(self):
        data = {}
        field_list = ('total_amount', 'paid_payment_amount', 'ongoing_payment_amount', 'recorded_payment_amount',
                      'remaining_payment_amount', 'remaining_include_recorded_payment_amount', 'normal_payment_amount')
        for i in field_list:
            data[i] = getattr(self, i, None)
        return data

    @property
    def contract_type(self):
        if self.contract_category == 'regular':
            return 'regular'
        role = self.job_position.role if self.job_position.role else None
        if role and role.name == '设计师':
            return 'design'
        return 'common'


# 工程师打款
class JobPayment(models.Model):
    STATUS = (
        (0, '记录'),
        (1, '启动'),
        (2, '完成'),
        (3, '异常'),
    )
    STATUS_ACTIONS_DICT = {
        0: {
            "status_display": "记录",
            "actions": {
                "start": {"result_status": 1}
            }
        },
        1: {
            "status_display": "启动",
            "actions": {
                "finish": {"result_status": 2},
                "cancel": {"result_status": 3}
            }
        }
    }
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='submitted_payments', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    status = models.IntegerField(verbose_name="状态", choices=STATUS, default=0)

    developer = models.ForeignKey('developers.Developer', related_name='payments', on_delete=models.CASCADE,
                                  null=True, blank=True)

    position = models.ForeignKey('projects.JobPosition', verbose_name='开发岗位', related_name='payments',
                                 on_delete=models.CASCADE, null=True, blank=True)

    name = models.CharField(max_length=50, verbose_name='姓名')
    bank_info = models.TextField(verbose_name='银行信息', null=True, blank=True)
    payment_reason = models.TextField(verbose_name='打款原因', null=True, blank=True)

    payee_name = models.CharField(max_length=50, verbose_name='收款人户名', null=True, blank=True)
    payee_id_card_number = models.CharField(max_length=30, verbose_name='收款人身份证号码', blank=True, null=True)
    payee_phone = models.CharField(max_length=20, verbose_name='收款人手机号', blank=True, null=True)
    payee_opening_bank = models.TextField(verbose_name='收款人开户行', blank=True, null=True)
    payee_account = models.CharField(verbose_name='收款人收款账号', null=True, blank=True, max_length=50)
    job_contract = models.ForeignKey(JobContract, verbose_name='工程师合同', related_name='payments', blank=True,
                                     null=True, on_delete=models.SET_NULL)

    amount = models.FloatField(verbose_name='额度')
    expected_at = models.DateField(verbose_name='期望日期')
    remarks = models.TextField(verbose_name='备注', blank=True, null=True)

    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, blank=True, null=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True, blank=True, null=True)
    start_at = models.DateTimeField(verbose_name="启动时间", blank=True, null=True)
    completed_at = models.DateField(verbose_name='完成日期', blank=True, null=True)
    comments = GenericRelation('comments.Comment', related_query_name="job_payments")
    logs = GenericRelation('logs.Log', related_query_name="job_payments")

    auto_tasks = GenericRelation(Task, object_id_field='source_id', content_type_field='source_type')

    def __str__(self):
        return '工程师:{} 金额:{}元'.format(self.name, self.amount)

    @property
    def manager(self):
        if self.project:
            return self.project.manager
        if self.job_contract:
            return self.job_contract.manager

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def project(self):
        if self.position:
            return self.position.project

    @property
    def comments_count(self):
        return self.comments.count()

    class Meta:
        verbose_name = '打款记录'
        permissions = (
            ("gear_view_all_developer_payments", "查看全部工程师打款"),
        )


class ProjectPayment(models.Model):
    STATUS = (
        ("process", "进行中"),
        ("completed", "正常完成"),
        ("termination", "异常终止"),
    )
    INVOICE_CHOICES = (
        ("general", "普票"),
        ("special", "专票"),
        ("none", "不需要"),
        ("invoice", "需要"),
    )
    TERMINATION_REASON = (
        ('contract_termination', '合同终止'),
        ('fill_error', '填写错误')
    )

    project = models.ForeignKey('projects.Project', verbose_name='项目', related_name='project_payments',
                                on_delete=models.CASCADE)
    contract_name = models.CharField(max_length=50, verbose_name='合同名称', null=True, blank=True)
    capital_account = models.CharField(max_length=50, verbose_name='付款账户', null=True, blank=True)

    total_amount = models.FloatField(verbose_name='总金额', null=True, blank=True)
    invoice = models.CharField(verbose_name="发票", max_length=50, choices=INVOICE_CHOICES, default='none')

    status = models.CharField(verbose_name="状态", max_length=50, choices=STATUS, default='process')
    remarks = models.TextField(verbose_name='备注', blank=True, null=True)

    close_remarks = models.TextField(verbose_name='终止备注', blank=True, null=True)
    termination_reason = models.CharField(verbose_name='终止原因', blank=True, null=True, max_length=32,
                                          choices=TERMINATION_REASON)
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name="修改时间", auto_now=True)

    def __str__(self):
        if self.contract_name:
            return self.contract_name
        else:
            return self.project.name + '项目收款'

    def save(self, *args, **kwargs):
        self.rebuild_status()
        super(ProjectPayment, self).save(*args, **kwargs)

    @classmethod
    def process_project_payments(cls):
        return cls.objects.filter(status='process')

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def termination_reason_display(self):
        return self.get_termination_reason_display()

    @property
    def invoice_display(self):
        return self.get_invoice_display()

    @property
    def need_invoice(self):
        return self.invoice != 'none'

    # 判断是否已完成：金额付清+发票已开
    def build_completed_status(self):
        if not self.is_fully_paid:
            return False
        need_invoice = self.need_invoice
        for stage in self.stages.all():
            if stage.receipted_amount != stage.receivable_amount:
                return False
            if need_invoice and stage.invoice == 'none':
                return False
        return True

    def rebuild_status(self):
        if self.build_completed_status():
            self.status = 'completed'
        elif self.status == 'completed':
            self.status = 'process'

    @property
    def is_fully_paid(self):
        if self.total_amount:
            return int(self.paid_total_amount) == int(self.total_amount)
        return True

    @property
    def paid_total_amount(self):
        total_amount = 0
        amount_list = []
        for stage in self.stages.all():
            if stage.receipted_amount:
                amount_list.append(stage.receipted_amount)
        if amount_list:
            total_amount = sum(amount_list)
        return total_amount

    @property
    def total_stage_count(self):
        return self.stages.count()

    @property
    def paid_stage_count(self):
        return self.paid_stages.count()

    @property
    def paid_stages(self):
        return self.stages.filter(receipted_amount__isnull=False).order_by('index')

    @property
    def need_paid_stage_count(self):
        return self.stages.count()

    def rebuild_stages_index(self):
        for index, stage in enumerate(self.stages.order_by('index', 'expected_date',
                                                           'created_at')):
            stage.index = index
            stage.save()

    def stages_auto_tasks(self, is_done=None):
        auto_tasks = Task.objects.none()
        for stage in self.stages.all():
            stage_auto_tasks = stage.auto_tasks
            if is_done is not None:
                stage_auto_tasks = stage_auto_tasks.filter(is_done=is_done)
            auto_tasks = auto_tasks | stage_auto_tasks
        return auto_tasks

    class Meta:
        verbose_name = '项目收款'


class ProjectPaymentStage(models.Model):
    INVOICE_CHOICES = (
        ("general", "普票"),
        ("special", "专票"),
        ("invoice", "已开"),
        ("none", "未开"),
    )
    # 应收：receivable、应付：payable、实收：receipts、实付：payment
    project_payment = models.ForeignKey(ProjectPayment, verbose_name='项目收款', related_name='stages',
                                        on_delete=models.CASCADE)
    index = models.IntegerField(verbose_name="排序位置", default=0)
    receivable_amount = models.FloatField(verbose_name='应收款')
    expected_date = models.DateField(verbose_name='预计日期', null=True, blank=True)

    receipted_amount = models.FloatField(verbose_name='已收款', null=True, blank=True)
    receipted_date = models.DateField(verbose_name='收款日期', null=True, blank=True)
    invoice = models.CharField(verbose_name='发票', max_length=15, choices=INVOICE_CHOICES, default='none')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    modified_at = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    auto_tasks = GenericRelation(Task, object_id_field='source_id', content_type_field='source_type')

    class Meta:
        verbose_name = '项目收款阶段'
        ordering = ['index']

    @property
    def is_fully_paid(self):
        return self.receipted_amount == self.receivable_amount

    @property
    def invoice_display(self):
        return self.get_invoice_display()
