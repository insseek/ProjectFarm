import json
from copy import deepcopy
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation

from auth_top.models import TopUser
from logs.utils import get_field_value
from projects.models import Project
from comments.models import Comment
from logs.models import Log


class TestCaseLibrary(models.Model):
    name = models.CharField(verbose_name='名称', max_length=50, unique=True)
    description = models.TextField(verbose_name='描述', blank=True, null=True)
    creator = models.ForeignKey(TopUser, verbose_name='创建人', related_name='test_case_libraries', blank=True,
                                null=True,
                                on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    logs = GenericRelation(Log, related_query_name="test_case_libraries")

    class Meta:
        verbose_name = '用例库'

    def __str__(self):
        return self.name


class TestCaseModule(models.Model):
    library = models.ForeignKey(TestCaseLibrary, verbose_name='用例库', related_name='modules',
                                on_delete=models.CASCADE)
    parent = models.ForeignKey(to='self', verbose_name='父级模块', related_name='children', on_delete=models.CASCADE,
                               blank=True,
                               null=True)
    name = models.CharField(verbose_name='名称', max_length=50)
    index = models.IntegerField(verbose_name="排序位置", default=0)
    creator = models.ForeignKey(TopUser, verbose_name='创建人',
                                related_name='creator_test_case_modules',
                                null=True,
                                on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    full_index = models.TextField(verbose_name='full_index', blank=True,
                                  null=True)
    full_name = models.TextField(verbose_name='full_name', blank=True,
                                 null=True)

    class Meta:
        verbose_name = '用例模块'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.index:
            self.index = self.get_new_index(parent=self.parent)
        self.full_index = self.build_full_index()
        self.full_name = self.build_full_name()
        super(TestCaseModule, self).save(*args, **kwargs)

    @classmethod
    def get_new_index(cls, parent=None):
        if not parent:
            last_obj = cls.objects.filter(parent__isnull=True).order_by('-index').first()
            if last_obj:
                return last_obj.index + 1
        else:
            last_obj = parent.children.order_by('-index').first()
            if last_obj:
                return last_obj.index + 1
        return 1

    @classmethod
    def get_module_contained_test_cases(cls, module):
        test_cases = module.test_cases.filter(is_active=True)
        for child in module.children.all():
            test_cases = test_cases | cls.get_module_contained_test_cases(child)
        return test_cases

    @property
    def contained_test_cases(self):
        return self.get_module_contained_test_cases(self)

    def build_full_index(self):
        return self.get_module_full_index(self)

    @classmethod
    def get_module_full_index(cls, module):
        index_str = str(module.index)
        if module.parent:
            index_str = cls.get_module_full_index(module.parent) + index_str
        return index_str

    def build_full_name(self):
        return self.get_module_full_name(self)

    @classmethod
    def get_module_full_name(cls, module):
        module_name = module.name
        if module.parent:
            module_name = '{parent_name}/{name}'.format(parent_name=cls.get_module_full_name(module.parent),
                                                        name=module_name)
        return module_name

    # 判断是否属于一个父级
    @property
    def parent_level(self):
        return self.library_id, self.parent_id

    # 获取同级兄弟
    @property
    def siblings(self):
        return TestCaseModule.objects.filter(library_id=self.library_id, parent_id=self.parent_id)

    # 获取同级兄弟
    @property
    def next_siblings(self):
        return self.siblings.filter(index__gt=self.index)

    # 获取同级兄弟
    @property
    def previous_siblings(self):
        return self.siblings.filter(index__lt=self.index)

    @property
    def tree_top_level(self):
        return self.library_id

    @property
    def tree_drag_sort_parent_verify_data(self):
        return None


class TestCase(models.Model):
    STATUS_CHOICES = (
        ('pending', '待评审'),
        ('approved', '通过'),
        ('rejected', '驳回')
    )
    index = models.IntegerField(verbose_name="排序位置", default=0)
    status = models.CharField(verbose_name="状态", max_length=15, choices=STATUS_CHOICES, default='pending')

    module = models.ForeignKey(TestCaseModule, verbose_name='模块', related_name='test_cases',
                               on_delete=models.CASCADE)
    description = models.TextField(verbose_name='描述')
    precondition = models.TextField(verbose_name='前置条件', null=True, blank=True)
    expected_result = models.TextField(verbose_name='预期结果')

    creator = models.ForeignKey(TopUser, verbose_name='创建人',
                                related_name='creator_test_cases',
                                null=True,
                                on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True, verbose_name="可用的")

    class Meta:
        verbose_name = '用例'

    def __str__(self):
        return self.description

    def save(self, *args, **kwargs):
        if not self.index:
            self.index = self.get_new_index(self.module)
        super(TestCase, self).save(*args, **kwargs)

    @classmethod
    def get_new_index(cls, module):
        last_obj = module.test_cases.filter(is_active=True).order_by('-index').first()
        if last_obj:
            return last_obj.index + 1
        return 1

    @classmethod
    def active_cases(cls):
        return cls.objects.filter(is_active=True).order_by('created_at')

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def library(self):
        return self.module.library

    # 判断是否属于一个父级
    @property
    def parent_level(self):
        return self.module_id

    # 获取同级兄弟
    @property
    def next_siblings(self):
        return self.siblings.filter(index__gt=self.index)

    # 获取同级兄弟
    @property
    def previous_siblings(self):
        return self.siblings.filter(index__lt=self.index)

    # 获取同级兄弟
    @property
    def siblings(self):
        return TestCase.objects.filter(is_active=True).filter(module_id=self.module_id)


class ProjectTestCaseLibrary(models.Model):
    project = models.OneToOneField(Project, verbose_name='项目', related_name='test_case_library',
                                   on_delete=models.CASCADE, null=True, blank=True, )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '项目用例库'

    def __str__(self):
        return '项目【{}】用例库'.format(self.project.name)


class ProjectPlatform(models.Model):
    DEFAULT_DATA = (
        'iOS',
        'Android',
        'Web',
        'H5',
        '小程序',
        '公众号',
        '管理后台'
    )
    project = models.ForeignKey(Project, verbose_name='项目', related_name='platforms', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    creator = models.ForeignKey(TopUser, verbose_name='创建人',
                                related_name='creator_project_platforms',
                                null=True,
                                on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '项目平台'
        unique_together = (('project', 'name'),)

    def __str__(self):
        return self.name

    @property
    def is_default(self):
        return self.name in self.DEFAULT_DATA

    @property
    def index(self):
        for index, p in enumerate(self.project.platforms.order_by('created_at')):
            if p.id == self.id:
                return index


class ProjectTag(models.Model):
    DEFAULT_DATA = (
        'Sprint 1',
        'Sprint 2',
        'Sprint 3',
        'Sprint 4',
        'Sprint 5',
        'Sprint 6'
    )
    project = models.ForeignKey(Project, verbose_name='项目', related_name='test_tags', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    index = models.IntegerField(verbose_name="排序位置", default=0)
    creator = models.ForeignKey(TopUser, verbose_name='创建人',
                                related_name='creator_test_tags',
                                null=True, blank=True,
                                on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '项目测试标签'
        unique_together = (('project', 'name'),)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.index:
            self.index = self.get_new_index()
        super(ProjectTag, self).save(*args, **kwargs)

    @classmethod
    def init_data(cls, project):
        for name in cls.DEFAULT_DATA:
            cls.objects.get_or_create(name=name, project_id=project.id)

    @classmethod
    def get_new_index(cls):
        obj = cls.objects.order_by('-index').first()
        if obj:
            return obj.index + 1
        return 1

    @property
    def is_default(self):
        return self.name in self.DEFAULT_DATA


class ProjectTestCaseModule(models.Model):
    project = models.ForeignKey(Project, verbose_name='项目', related_name='test_case_modules',
                                on_delete=models.CASCADE)
    parent = models.ForeignKey(to='self', verbose_name='父级模块', related_name='children', on_delete=models.CASCADE,
                               blank=True,
                               null=True)
    name = models.CharField(verbose_name='名称', max_length=50)
    index = models.IntegerField(verbose_name="排序位置", default=0)
    platforms = models.ManyToManyField(ProjectPlatform, verbose_name='平台', related_name='test_case_modules')
    creator = models.ForeignKey(TopUser, verbose_name='创建人',
                                related_name='creator_project_test_case_modules',
                                null=True, blank=True,
                                on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    full_index = models.TextField(verbose_name='full_index', blank=True,
                                  null=True)
    full_name = models.TextField(verbose_name='full_name', blank=True,
                                 null=True)

    class Meta:
        verbose_name = '项目用例模块'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.index:
            self.index = self.get_new_index(parent=self.parent)
        self.full_index = self.build_full_index()
        self.full_name = self.build_full_name()
        super(ProjectTestCaseModule, self).save(*args, **kwargs)

    @classmethod
    def get_new_index(cls, parent=None):
        if not parent:
            last_obj = cls.objects.filter(parent__isnull=True).order_by('-index').first()
            if last_obj:
                return last_obj.index + 1
        else:
            last_obj = parent.children.order_by('-index').first()
            if last_obj:
                return last_obj.index + 1
        return 1

    @classmethod
    def get_module_contained_test_cases(cls, module):
        test_cases = module.test_cases.filter(is_active=True)
        for child in module.children.all():
            test_cases = test_cases | cls.get_module_contained_test_cases(child)
        return test_cases

    @property
    def contained_test_cases(self):
        return self.get_module_contained_test_cases(self)

    @classmethod
    def get_module_contained_bugs(cls, module):
        test_cases = module.bugs.all()
        for child in module.children.all():
            test_cases = test_cases | cls.get_module_contained_bugs(child)
        return test_cases

    @property
    def contained_bugs(self):
        return self.get_module_contained_bugs(self)

    @classmethod
    def get_module_descendants(cls, module):
        descendants = module.children.all()
        for child in module.children.all():
            descendants = descendants | cls.get_module_descendants(child)
        return descendants

    @property
    def descendants(self):
        return self.get_module_descendants(self)

    def build_full_index(self):
        return self.get_module_full_index(self)

    @classmethod
    def get_module_full_index(cls, module):
        index_str = str(module.index)
        if module.parent:
            index_str = cls.get_module_full_index(module.parent) + index_str
        return index_str

    def build_full_name(self):
        return self.get_module_full_name(self)

    @classmethod
    def get_module_full_name(cls, module):
        module_name = module.name
        if module.parent:
            module_name = '{parent_name}/{name}'.format(parent_name=cls.get_module_full_name(module.parent),
                                                        name=module_name)
        return module_name

    # 判断是否属于一个父级
    @property
    def parent_level(self):
        return self.project_id, self.parent_id

    # 获取同级兄弟
    @property
    def siblings(self):
        return ProjectTestCaseModule.objects.filter(project_id=self.project_id, parent_id=self.parent_id)

    # 获取同级兄弟
    @property
    def next_siblings(self):
        return self.siblings.filter(index__gt=self.index)

    # 获取同级兄弟
    @property
    def previous_siblings(self):
        return self.siblings.filter(index__lt=self.index)

    @property
    def tree_top_level(self):
        return self.project_id

    @property
    def tree_drag_sort_parent_verify_data(self):
        return set(self.platforms.values_list('id', flat=True))

    @property
    def tree_drag_sort_error_message(self):
        return "父级模块不包含被移动模块的平台，不能移动"


class ProjectTestCase(models.Model):
    STATUS_CHOICES = (
        ('pending', '待评审'),
        ('approved', '通过'),
        ('rejected', '驳回')
    )
    CASE_TYPE = (
        ('smoking', '冒烟用例'),
        ('no_smoking', '非冒烟用例')
    )
    FLOW_TYPE = (
        ('main_process', '主流程用例'),
        ('others', '其他类型用例')
    )
    index = models.IntegerField(verbose_name="排序位置", default=0)
    status = models.CharField(verbose_name="状态", max_length=15, choices=STATUS_CHOICES, default='pending')

    project = models.ForeignKey(Project, verbose_name='项目', related_name='test_cases', on_delete=models.CASCADE)
    module = models.ForeignKey(ProjectTestCaseModule, verbose_name='模块', related_name='test_cases',
                               null=True, blank=True,
                               on_delete=models.SET_NULL)
    platforms = models.ManyToManyField(ProjectPlatform, verbose_name='平台', related_name='test_cases')
    tags = models.ManyToManyField(ProjectTag, verbose_name='标签', related_name='test_cases')

    description = models.TextField(verbose_name='描述')
    precondition = models.TextField(verbose_name='前置条件', null=True, blank=True)
    expected_result = models.TextField(verbose_name='预期结果')
    case_type = models.CharField(verbose_name='用例类型', choices=CASE_TYPE, default='no_smoking', max_length=20)
    flow_type = models.CharField(verbose_name='流程类型', choices=FLOW_TYPE, default='others', max_length=20)

    creator = models.ForeignKey(TopUser, verbose_name='创建人',
                                related_name='creator_project_test_cases',
                                null=True, blank=True,
                                on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True, verbose_name="可用的")

    execution_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = '项目用例'

    def __str__(self):
        return self.description

    def save(self, *args, **kwargs):
        if not self.index:
            self.index = self.get_new_index(self.module)
        self.execution_count = self.build_execution_count()
        super(ProjectTestCase, self).save(*args, **kwargs)

    @classmethod
    def get_new_index(cls, module):
        last_obj = module.test_cases.filter(is_active=True).order_by('-index').first()
        if last_obj:
            return last_obj.index + 1
        return 1

    @classmethod
    def active_cases(cls):
        return cls.objects.filter(is_active=True).order_by('created_at')

    @property
    def status_display(self):
        return self.get_status_display()

    def build_execution_count(self):
        return self.plan_cases.filter(status__in=['failed', 'pass']).count()

    def rebuild_execution_count(self):
        self.execution_count = self.build_execution_count()
        self.save()

    # 判断是否属于一个父级
    @property
    def parent_level(self):
        return self.module_id

    # 获取同级兄弟
    @property
    def next_siblings(self):
        return self.siblings.filter(index__gt=self.index)

    # 获取同级兄弟
    @property
    def previous_siblings(self):
        return self.siblings.filter(index__lt=self.index)

    # 获取同级兄弟
    @property
    def siblings(self):
        return ProjectTestCase.objects.filter(is_active=True).filter(module_id=self.module_id)


class ProjectTestPlan(models.Model):
    STATUS_CHOICES = (
        ('not_start', '未开始'),
        ('ongoing', '进行中'),
        ('done', '已完成'),
    )
    TEST_TYPE = (
        ('full_volume', '全量测试'),
        ('smoking', '冒烟测试'),
        ('main_process', '主流程测试'),
    )
    EXECUTE_TYPE = (
        (0, 'O次'),
        (1, '1次'),
        (2, '2次'),
        (3, '3次以上'),
    )
    index = models.IntegerField(verbose_name="序号", default=0)
    status = models.CharField(verbose_name="状态", max_length=15, choices=STATUS_CHOICES, default='not_start')
    name = models.CharField(verbose_name="计划名称", max_length=50, blank=True, null=True)
    project = models.ForeignKey(Project, verbose_name='项目', related_name='test_plans', on_delete=models.CASCADE)
    platform = models.ForeignKey(ProjectPlatform, verbose_name='平台', related_name='test_plans',
                                 on_delete=models.CASCADE)
    environment = models.TextField(verbose_name='测试环境')

    remarks = models.TextField(verbose_name="备注", blank=True, null=True)

    creator = models.ForeignKey(TopUser, verbose_name='创建人',
                                related_name='creator_project_test_plans',
                                null=True, blank=True,
                                on_delete=models.SET_NULL)
    executors = models.ManyToManyField(TopUser, verbose_name='执行人',
                                       related_name='executor_project_test_plans')
    full_volume_test = models.BooleanField(verbose_name='全量测试', default=False)
    test_type = models.CharField(verbose_name='测试类型', choices=TEST_TYPE, default='full_volume', max_length=20)
    case_tags = models.ManyToManyField(ProjectTag, verbose_name='用例标签', related_name='project_test_plans')
    execute_count = models.IntegerField(verbose_name='执行次数', choices=EXECUTE_TYPE, null=True, blank=True)
    project_module_count = models.IntegerField(verbose_name='项目模块数', null=True, blank=True)
    module_count = models.IntegerField(verbose_name='所选模块数', null=True, blank=True)

    expected_start_time = models.DateTimeField(verbose_name='预计测试开始时间', null=True, blank=True)
    expected_end_time = models.DateTimeField(verbose_name='预计测试结束时间', null=True, blank=True)
    practical_start_time = models.DateTimeField(verbose_name='实际测试开始时间', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    done_at = models.DateTimeField(verbose_name='完成时间', null=True, blank=True)

    execution_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = '项目测试计划'

    def save(self, *args, **kwargs):
        if not self.index:
            self.index = self.get_new_index(self.project)
        super(ProjectTestPlan, self).save(*args, **kwargs)

    @classmethod
    def get_new_index(cls, project):
        obj = project.test_plans.order_by('-index').first()
        if obj:
            return obj.index + 1
        return 1

    @property
    def is_done(self):
        return self.status == 'done'

    @property
    def execution_count(self):
        return self.plan_cases.filter(status__in=['failed', 'pass']).count()

    @property
    def status_display(self):
        return self.get_status_display()


class TestPlanModule(models.Model):
    plan = models.ForeignKey(ProjectTestPlan, verbose_name='测试计划', related_name='plan_modules',
                             on_delete=models.CASCADE)
    module = models.ForeignKey(ProjectTestCaseModule, verbose_name='项目用例模块', related_name='plan_modules',
                               null=True, blank=True,
                               on_delete=models.SET_NULL)
    parent = models.ForeignKey(to='self', verbose_name='父级模块', related_name='children', on_delete=models.CASCADE,
                               blank=True,
                               null=True)
    name = models.CharField(verbose_name='名称', max_length=50)
    index = models.IntegerField(verbose_name="排序位置", default=0)
    creator = models.ForeignKey(TopUser, verbose_name='创建人',
                                related_name='creator_test_plan_modules',
                                null=True, blank=True,
                                on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    full_index = models.TextField(verbose_name='full_index', blank=True,
                                  null=True)
    full_name = models.TextField(verbose_name='full_name', blank=True,
                                 null=True)

    class Meta:
        verbose_name = '测试计划的模块'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.index:
            self.index = self.get_new_index(parent=self.parent)
        self.full_index = self.build_full_index()
        self.full_name = self.build_full_name()
        super(TestPlanModule, self).save(*args, **kwargs)

    @classmethod
    def get_new_index(cls, parent=None):
        if not parent:
            last_obj = cls.objects.filter(parent__isnull=True).order_by('-index').first()
            if last_obj:
                return last_obj.index + 1
        else:
            last_obj = parent.children.order_by('-index').first()
            if last_obj:
                return last_obj.index + 1
        return 1

    def build_full_index(self):
        return self.get_module_full_index(self)

    @classmethod
    def get_module_full_index(cls, module):
        index_str = str(module.index)
        if module.parent:
            index_str = cls.get_module_full_index(module.parent) + index_str
        return index_str

    def build_full_name(self):
        return self.get_module_full_name(self)

    @classmethod
    def get_module_full_name(cls, module):
        module_name = module.name
        if module.parent:
            module_name = '{parent_name}/{name}'.format(parent_name=cls.get_module_full_name(module.parent),
                                                        name=module_name)
        return module_name

    @classmethod
    def get_module_contained_test_cases(cls, module):
        cases = module.plan_cases.all()
        for child in module.children.all():
            cases = cases | cls.get_module_contained_test_cases(child)
        return cases

    @property
    def contained_test_cases(self):
        return self.get_module_contained_test_cases(self)


class TestPlanCase(models.Model):
    STATUS_CHOICES = (
        ('pending', '未执行'),
        ('pass', '通过'),
        ('failed', '失败')
    )
    CASE_TYPE = (
        ('smoking', '冒烟用例'),
        ('no_smoking', '非冒烟用例')
    )
    FLOW_TYPE = (
        ('main_process', '主流程用例'),
        ('others', '其他类型用例')
    )
    index = models.IntegerField(verbose_name="排序位置", default=0)
    status = models.CharField(verbose_name="状态", max_length=15, choices=STATUS_CHOICES, default='pending')

    project = models.ForeignKey(Project, verbose_name='项目', related_name='plan_cases',
                                on_delete=models.CASCADE)
    plan = models.ForeignKey(ProjectTestPlan, verbose_name='测试计划', related_name='plan_cases',
                             on_delete=models.CASCADE)
    module = models.ForeignKey(TestPlanModule, verbose_name='模块', related_name='plan_cases',
                               on_delete=models.CASCADE)

    case = models.ForeignKey(ProjectTestCase, verbose_name='项目用例', related_name='plan_cases',
                             null=True, blank=True,
                             on_delete=models.SET_NULL)
    description = models.TextField(verbose_name='描述')
    precondition = models.TextField(verbose_name='前置条件', null=True, blank=True)
    expected_result = models.TextField(verbose_name='预期结果')

    tags = models.ManyToManyField(ProjectTag, verbose_name='标签', related_name='plan_cases')
    creator = models.ForeignKey(TopUser, verbose_name='创建人',
                                null=True, blank=True,
                                related_name='creator_plan_cases',
                                on_delete=models.SET_NULL)
    executor = models.ForeignKey(TopUser, verbose_name='执行人',
                                 related_name='executor_plan_cases',
                                 null=True, blank=True,
                                 on_delete=models.SET_NULL)
    case_type = models.CharField(verbose_name='用例类型', choices=CASE_TYPE, default='no_smoking', max_length=20)
    flow_type = models.CharField(verbose_name='流程类型', choices=FLOW_TYPE, default='others', max_length=20)
    executed_at = models.DateTimeField(verbose_name='执行时间', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(verbose_name='关闭时间', null=True, blank=True)

    class Meta:
        verbose_name = '测试计划的用例'

    def __str__(self):
        return self.description

    def save(self, *args, **kwargs):
        if not self.index:
            self.index = self.get_new_index(self.module)
        super(TestPlanCase, self).save(*args, **kwargs)

    @classmethod
    def get_new_index(cls, module):
        last_obj = module.plan_cases.order_by('-index').first()
        if last_obj:
            return last_obj.index + 1
        return 1

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def platform(self):
        return self.plan.platform


class Bug(models.Model):
    STATUS_CHOICES = (
        ('pending', '待修复'),
        ('fixed', '已修复'),
        ('confirmed', '修复关闭'),
        ('closed', '无效关闭')
    )
    # 全部的操作  指派、修复、确认修复、无效关闭、激活
    ACTIONS = ['assign', 'fix', 'confirm', 'close', 'reopen']

    # 每个状态可以进行的的操作
    STATUS_ACTIONS_CHOICES = {
        "pending": ['assign', 'fix', 'close'],
        "fixed": ['assign', 'reopen', 'confirm', 'close'],
        "confirmed": ['reopen'],
        "closed": ['reopen'],
    }

    # 每个操作后对应的状态
    ACTIONS_TO_STATUS = {
        'fix': 'fixed',
        'confirm': 'confirmed',
        'close': 'closed',
        'reopen': 'pending'
    }
    # 可以进行该操作的对应的状态
    ACTIONS_FROM_STATUS = {
        'assign': ['pending', 'fixed'],
        'fix': ['pending'],
        'confirm': ['fixed'],
        'close': ['pending', 'fixed'],
        'reopen': ['fixed', 'confirmed', 'closed'],
    }

    PRIORITY_CHOICES = (
        ('P0', 'P0'),
        ('P1', 'P1'),
        ('P2', 'P2'),
        ('P3', 'P3'),
    )
    BUG_TYPE_CHOICES = (
        ('function', '功能'),
        ('ui', 'UI'),
        ('requirement', '需求'),
        ('api', '接口'),
        ('performance', '性能'),
        ('other', '其他'),
    )

    project = models.ForeignKey(Project, verbose_name='项目', related_name='bugs',
                                on_delete=models.CASCADE)
    # 测试计划用例转bug
    plan_case = models.ForeignKey(TestPlanCase, verbose_name='用例执行', related_name='bugs',
                                  null=True, blank=True,
                                  on_delete=models.SET_NULL)
    index = models.IntegerField(verbose_name="排序位置", default=0)
    title = models.CharField(verbose_name='标题', max_length=100)

    description = models.TextField(verbose_name='描述')
    description_text = models.TextField(verbose_name='描述文本', null=True, blank=True)

    priority = models.CharField(verbose_name="优先级", max_length=10, choices=PRIORITY_CHOICES)
    bug_type = models.CharField(verbose_name="bug类型", max_length=25, choices=BUG_TYPE_CHOICES)

    module = models.ForeignKey(ProjectTestCaseModule, verbose_name='模块', related_name='bugs',
                               null=True, blank=True,
                               on_delete=models.SET_NULL)
    platform = models.ForeignKey(ProjectPlatform, verbose_name='平台', related_name='bugs', null=True, blank=True,
                                 on_delete=models.SET_NULL)
    tags = models.ManyToManyField(ProjectTag, verbose_name='标签', related_name='bugs')

    status = models.CharField(verbose_name="状态", max_length=15, choices=STATUS_CHOICES, default='pending')

    assignee = models.ForeignKey(TopUser, verbose_name='分配人',
                                 related_name='assignee_bugs',
                                 null=True, blank=True,
                                 on_delete=models.SET_NULL)

    creator = models.ForeignKey(TopUser, verbose_name='创建人',
                                related_name='created_bugs',
                                null=True, blank=True,
                                on_delete=models.SET_NULL)
    comments = GenericRelation(Comment, related_query_name="projects")

    fixed_by = models.ForeignKey(TopUser, verbose_name='修复人',
                                 related_name='fixed_bugs',
                                 null=True, blank=True,
                                 on_delete=models.SET_NULL)
    closed_by = models.ForeignKey(TopUser, verbose_name='关闭人',
                                  related_name='closed_bugs',
                                  null=True, blank=True,
                                  on_delete=models.SET_NULL)
    reopened_by = models.ForeignKey(TopUser, verbose_name='激活人',
                                    related_name='reopened_bugs',
                                    null=True, blank=True,
                                    on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fixed_at = models.DateTimeField(verbose_name='修复时间', null=True, blank=True)
    closed_at = models.DateTimeField(verbose_name='关闭时间', null=True, blank=True)

    reopened_at = models.DateTimeField(verbose_name='激活时间', null=True, blank=True)

    class Meta:
        verbose_name = '项目Bug'
        # unique_together = (('project', 'index'),)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.index:
            self.index = self.get_new_index(self.project)

        if self.status in ['confirmed', 'closed']:
            if not self.closed_at:
                self.closed_at = timezone.now()
        elif self.status == 'fixed':
            self.closed_at = None
            if not self.fixed_at:
                self.fixed_at = timezone.now()
        elif self.status == 'pending':
            self.fixed_at = None
            self.closed_at = None

        super(Bug, self).save(*args, **kwargs)

    @classmethod
    def pending_bugs(cls, queryset=None):
        if queryset is not None:
            return queryset.filter(status='pending')
        return cls.objects.filter(status='pending')

    @classmethod
    def get_status_value_display(cls, value):
        for v, l in cls.STATUS_CHOICES:
            if value == v:
                return l

    @classmethod
    def get_new_index(cls, project):
        obj = project.bugs.order_by('-index').first()
        if obj:
            return obj.index + 1
        return 1

    @property
    def priority_display(self):
        return self.get_priority_display()

    @property
    def bug_type_display(self):
        return self.get_bug_type_display()

    @property
    def status_display(self):
        return self.get_status_display()

    @classmethod
    def priority_index(cls, value):
        for index, (v, l) in enumerate(cls.PRIORITY_CHOICES):
            if value == v:
                return index

    @classmethod
    def bug_type_index(cls, value):
        for index, (v, l) in enumerate(cls.BUG_TYPE_CHOICES):
            if value == v:
                return index

    @classmethod
    def status_index(cls, value):
        for index, (v, l) in enumerate(cls.STATUS_CHOICES):
            if value == v:
                return index

    @property
    def comments_count(self):
        count = 0
        for log in self.operation_logs.all():
            count = count + len(log.comments.all())
        return count

    @property
    def module_full_name(self):
        if self.module:
            return self.module.full_name


class BugOperationLog(models.Model):
    TYPE_CHOICES = (
        ('create', '创建'),
        ('edit', '编辑'),
        ('assign', '指派'),
        ('fix', '修复'),
        ('confirm', '确认修复'),
        ('close', '关闭'),
        ('reopen', '激活'),
        ('comment', '评论'),
        ('other', '操作'),
    )
    bug = models.ForeignKey(Bug, verbose_name='Bug', related_name='operation_logs', on_delete=models.CASCADE)
    operator = models.ForeignKey(TopUser, related_name='bug_operation_logs', verbose_name='操作人', null=True, blank=True,
                                 on_delete=models.SET_NULL)
    remarks = models.TextField(verbose_name='备注', null=True, blank=True)
    log_type = models.CharField(verbose_name="操作类型", max_length=15, choices=TYPE_CHOICES, default='other')
    origin_assignee = models.ForeignKey(TopUser, verbose_name='原分配人',
                                        null=True, blank=True,
                                        related_name='origin_assignee_bug_operation_logs',
                                        on_delete=models.SET_NULL)
    new_assignee = models.ForeignKey(TopUser, verbose_name='新分配人',
                                     null=True, blank=True,
                                     related_name='new_assignee_bug_operation_logs',
                                     on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    created_date = models.DateField(auto_now_add=True)

    comments = GenericRelation(Comment, related_query_name="bug_operation_logs")

    class Meta:
        verbose_name = 'Bug操作记录'

    def __str__(self):
        return "{}{}了bug".format(self.operator.username, self.get_log_type_display())

    @classmethod
    def build_log(cls, bug, operator, log_type='other', remarks=None, origin_assignee=None, new_assignee=None,
                  comment=None):
        log = cls(bug=bug, operator=operator, log_type=log_type, remarks=remarks, origin_assignee=origin_assignee,
                  new_assignee=new_assignee)
        log.save()
        if comment:
            Comment.objects.create(creator=operator, content=comment, content_object=log)
        return log

    @classmethod
    def build_comment_log(cls, bug, operator, content, content_text=None, parent=None):
        if not parent:
            log = cls.objects.create(bug=bug, operator=operator, log_type="comment")
            Comment.objects.create(creator=operator, content=content, content_text=content_text, content_object=log)
        else:
            if getattr(parent.content_object, 'bug') == bug and not parent.parent:
                Comment.objects.create(creator=operator, content=content, content_text=content_text,
                                       content_object=parent.content_object, parent=parent)


class TestCaseReviewLog(models.Model):
    TYPE_CHOICES = (
        ('create', '创建'),
        ('edit', '编辑'),
        ('pending', '待评审'),
        ('approved', '通过'),
        ('rejected', '驳回'),
        ('other', '其它'),
    )
    case = models.ForeignKey(TestCase, verbose_name='项目用例', related_name='review_logs',
                             null=True, blank=True, on_delete=models.SET_NULL)
    operator = models.ForeignKey(TopUser, related_name='test_case_review_logs', verbose_name='操作人',
                                 null=True, blank=True, on_delete=models.SET_NULL)
    remarks = models.TextField(verbose_name='备注', null=True, blank=True)
    log_type = models.CharField(verbose_name="操作类型", max_length=15, choices=TYPE_CHOICES, default='other')
    content_data = models.TextField(verbose_name='内容数据', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = '用例评审记录'

    def __str__(self):
        return "{}{}了用例".format(self.operator.username, self.get_log_type_display())

    @classmethod
    def build_create_object_log(cls, operator, created_object):
        if not operator.is_authenticated:
            return None
        model_name = created_object._meta.model_name
        title = '新建' + created_object._meta.verbose_name
        subtitle = str(created_object)
        content_data = {"type": "create", "model_name": model_name, "title": title, "subtitle": subtitle, "fields": []}
        fields = created_object._meta.get_fields()
        for field in fields:
            if not field.editable:
                continue
            new_value = get_field_value(created_object, field)
            name = field.name
            verbose_name = field.verbose_name
            op_data = {"type": "create", "name": name, "verbose_name": verbose_name,
                       "value": new_value}
            content_data["fields"].append(op_data)

        return cls.build_log(operator, created_object, log_type='create', content_data=content_data)

    @classmethod
    def build_update_object_log(cls, operator, original, updated):
        if not operator.is_authenticated:
            return None
        model_name = updated._meta.model_name
        title = '修改' + updated._meta.verbose_name
        subtitle = str(updated)
        content_data = {"type": "update", "model_name": model_name, "title": title, "subtitle": subtitle, "fields": []}
        fields = updated._meta.get_fields()
        for field in fields:
            if not field.editable:
                continue
            # 多对多deepcopy存不了
            if isinstance(field, models.ManyToManyField):
                continue
            old_value = get_field_value(original, field)
            new_value = get_field_value(updated, field)
            if old_value != new_value:
                name = field.name
                verbose_name = field.verbose_name
                op_data = {"type": "update", "name": name, "verbose_name": verbose_name,
                           "old_value": old_value,
                           "new_value": new_value}
                content_data["fields"].append(op_data)
        if content_data["fields"]:
            return cls.build_log(operator, updated, log_type='edit', content_data=content_data)

    @classmethod
    def build_log(cls, operator, case, log_type='other', content_data=None, remarks=None):
        if content_data:
            content_data = json.dumps(content_data, ensure_ascii=False)
        log = cls(case=case, operator=operator, log_type=log_type, content_data=content_data, remarks=remarks)
        log.save()
        return log


class ProjectTestCaseReviewLog(models.Model):
    TYPE_CHOICES = (
        ('create', '创建'),
        ('edit', '编辑'),
        ('approved', '通过'),
        ('rejected', '驳回'),
        ('other', '其它'),
    )
    case = models.ForeignKey(ProjectTestCase, verbose_name='项目用例', related_name='review_logs',
                             null=True, blank=True, on_delete=models.SET_NULL)
    operator = models.ForeignKey(TopUser, related_name='project_test_case_review_logs', verbose_name='操作人',
                                 null=True, blank=True, on_delete=models.SET_NULL)
    remarks = models.TextField(verbose_name='备注', null=True, blank=True)
    log_type = models.CharField(verbose_name="操作类型", max_length=15, choices=TYPE_CHOICES, default='other')
    content_data = models.TextField(verbose_name='内容数据', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = '项目用例评审记录'

    def __str__(self):
        return "{}{}了用例".format(self.operator.username, self.get_log_type_display())

    @classmethod
    def build_create_object_log(cls, operator, created_object, remarks=None):
        if not operator.is_authenticated:
            return None
        model_name = created_object._meta.model_name
        title = '新建' + created_object._meta.verbose_name
        subtitle = str(created_object)
        content_data = {"type": "create", "model_name": model_name, "title": title, "subtitle": subtitle, "fields": []}
        fields = created_object._meta.get_fields()
        for field in fields:
            if field.editable:
                new_value = get_field_value(created_object, field)
                name = field.name
                verbose_name = field.verbose_name
                op_data = {"type": "create", "name": name, "verbose_name": verbose_name,
                           "value": new_value}
                content_data["fields"].append(op_data)

        return cls.build_log(operator, created_object, log_type='create', content_data=content_data, remarks=remarks)

    @classmethod
    def build_update_object_log(cls, operator, original, updated, remarks=None):
        if not operator.is_authenticated:
            return None
        model_name = updated._meta.model_name
        title = '修改' + updated._meta.verbose_name
        subtitle = str(updated)
        content_data = {"type": "update", "model_name": model_name, "title": title, "subtitle": subtitle, "fields": []}
        fields = updated._meta.get_fields()
        for field in fields:
            if not field.editable:
                continue
            # 多对多deepcopy存不了
            if isinstance(field, models.ManyToManyField):
                continue

            old_value = get_field_value(original, field)
            new_value = get_field_value(updated, field)
            if old_value != new_value:
                name = field.name
                verbose_name = field.verbose_name
                op_data = {"type": "update", "name": name, "verbose_name": verbose_name,
                           "old_value": old_value,
                           "new_value": new_value}
                content_data["fields"].append(op_data)
        if content_data["fields"]:
            return cls.build_log(operator, updated, log_type='edit', content_data=content_data, remarks=remarks)

    @classmethod
    def build_log(cls, operator, case, log_type='other', content_data=None, remarks=None):
        if content_data:
            content_data = json.dumps(content_data, ensure_ascii=False)
        log = cls(case=case, operator=operator, log_type=log_type, content_data=content_data, remarks=remarks)
        log.save()
        return log


class ProjectTestCaseExecuteLog(models.Model):
    TYPE_CHOICES = (
        ('pass', '通过'),
        ('failed', '失败'),
        ('create_bug', '创建bug'),
        ('relevance_bug', '关联bug'),
    )
    STATUS_CHOICES = (
        ('pending', '未执行'),
        ('pass', '通过'),
        ('failed', '失败'),
    )
    case = models.ForeignKey(ProjectTestCase, verbose_name='项目用例', related_name='executed_logs',
                             null=True, blank=True, on_delete=models.SET_NULL)
    plan = models.ForeignKey(ProjectTestPlan, verbose_name='测试计划', related_name='case_executed_logs',
                             on_delete=models.CASCADE)
    plan_case = models.ForeignKey(TestPlanCase, verbose_name='用例执行', related_name='executed_logs',
                                  null=True, blank=True, on_delete=models.SET_NULL)
    operator = models.ForeignKey(TopUser, related_name='test_plan_case_execute_logs', verbose_name='操作人', null=True,
                                 blank=True, on_delete=models.SET_NULL)
    executed_at = models.DateTimeField(verbose_name="执行时间", auto_now_add=True)
    executed_type = models.CharField(verbose_name="执行类型", max_length=20, choices=TYPE_CHOICES)
    executed_status = models.CharField(verbose_name="执行后状态", max_length=20, choices=STATUS_CHOICES)
    bug = models.ForeignKey(Bug, verbose_name='Bug', related_name='test_plan_case_execute_logs',
                            on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        verbose_name = '项目用例执行记录'

    def __str__(self):
        return "{}{}执行{}".format(self.executed_at, self.operator.username, self.get_executed_status_display())

    @classmethod
    def build_log(cls, operator, plan_case, executed_type, executed_status, bug=None):
        plan = plan_case.plan
        case = plan_case.case
        log = cls(case=case, plan=plan, plan_case=plan_case, operator=operator, executed_type=executed_type, bug=bug,
                  executed_status=executed_status)
        log.save()
        return log


class TestDayStatistic(models.Model):
    operator = models.ForeignKey(TopUser, verbose_name='操作人',
                                 related_name='test_day_statistics', on_delete=models.CASCADE)
    opened_bugs = models.IntegerField(verbose_name='新增bug数', default=0)
    closed_bugs = models.IntegerField(verbose_name='关闭BUG数', default=0)
    created_cases = models.IntegerField(verbose_name='新增项目用例数', default=0)
    executed_cases = models.IntegerField(verbose_name='执行用例次数', default=0)
    projects_detail = models.TextField(verbose_name='每个项目的数据详情', default='[]')
    date = models.DateField()

    class Meta(object):
        verbose_name = '测试数据统计'
        unique_together = (('operator', 'date'),)


class TestMonthStatistic(models.Model):
    operator = models.ForeignKey(TopUser, verbose_name='操作人',
                                 related_name='test_month_statistics', on_delete=models.CASCADE)
    opened_bugs = models.IntegerField(verbose_name='新增bug数', default=0)
    closed_bugs = models.IntegerField(verbose_name='关闭BUG数', default=0)
    created_cases = models.IntegerField(verbose_name='新增项目用例数', default=0)
    executed_cases = models.IntegerField(verbose_name='执行用例次数', default=0)
    projects_detail = models.TextField(verbose_name='每个项目的数据详情', default='[]')
    # 'YYYY-MM'
    month = models.CharField(verbose_name='月份', max_length=20)
    month_first_day = models.DateField(verbose_name='本月第一天')

    class Meta(object):
        verbose_name = 'bug与项目用例月统计'
        unique_together = (('operator', 'month_first_day'),)


# 燃尽图
class TestDayBugStatistic(models.Model):
    project = models.ForeignKey(Project, verbose_name='项目', related_name='day_bugs_statistic',
                                on_delete=models.CASCADE)
    bugs_detail = models.TextField(verbose_name='待修复bug数优先级统计数据', default='{}')
    date = models.DateField()

    class Meta(object):
        verbose_name = '测试数据统计'
        unique_together = (('project', 'date'),)
