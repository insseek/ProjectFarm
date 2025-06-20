from django.contrib.auth.models import User, Group
from rest_framework import serializers

from farmbase.models import Profile, FunctionPermission, Documents, FunctionModule, TeamUser, Team
from farmbase.permissions_utils import get_user_function_perms
from geargitlab.tasks import get_gitlab_user_data, get_gitlab_user_simple_data


class UserField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        users = User.objects.filter(pk=value.pk)
        if users.exists():
            user = users[0]
        else:
            return None

        avatar_url = None
        if user.profile.avatar:
            avatar_url = user.profile.avatar.url
        avatar_color = user.profile.avatar_color
        dict = {"id": value.pk, "username": user.username, "avatar_url": avatar_url, 'avatar_color': avatar_color,
                'is_active': user.is_active}
        return dict


class GroupField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        group = Group.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": group.name}
        return dict


class FunctionModuleField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        func_module = FunctionModule.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": func_module.name, "codename": func_module.codename}
        return dict


class FunctionPermField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        func_perm = FunctionPermission.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": func_perm.name, 'codename': func_perm.codename}
        return dict


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_active')


class UserFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'is_active')


class UserBasicSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    avatar_color = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'avatar_url', 'avatar_color', 'avatar', 'is_active', 'phone')

    def get_phone(self, obj):
        return obj.profile.phone

    def get_avatar(self, obj):
        if obj.profile.avatar:
            return obj.profile.avatar.url

    def get_avatar_url(self, obj):
        if obj.profile.avatar:
            return obj.profile.avatar.url

    def get_avatar_color(self, obj):
        return obj.profile.avatar_color


class UserWithGroupSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    avatar_color = serializers.SerializerMethodField()
    default_avatar = serializers.SerializerMethodField()

    groups = GroupField(many=True, queryset=Group.objects.all(), required=False)
    teams = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'groups', 'avatar_url', 'avatar_color', 'default_avatar', 'is_active', 'teams')

    def get_avatar_url(self, obj):
        if obj.profile.avatar:
            return obj.profile.avatar.url

    def get_avatar_color(self, obj):
        return obj.profile.avatar_color

    def get_default_avatar(self, obj):
        if obj.profile.avatar:
            return obj.profile.avatar.url
        return "/static/base/images/default_avatar_img.svg"

    def get_teams(self, obj):
        data = []
        if obj.team_users.all():
            for team_user in obj.team_users.all():
                team = team_user.team
                team_data = {'id': team.id, 'name': team.name}
                data.append(team_data)
        return data


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')
        read_only_fields = ('id',)


class GroupWithUsersSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ('id', 'name', 'users')
        read_only_fields = ('id', 'users')

    def get_users(self, obj):
        user_set = obj.user_set.filter(is_active=True).all()
        data = UserBasicSerializer(user_set, many=True).data
        return data


class ProfileSerializer(serializers.ModelSerializer):
    gitlab_user = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = '__all__'

    def get_gitlab_user(self, obj):
        if obj.gitlab_user_id:
            return get_gitlab_user_data(obj.gitlab_user_id)


class ProfileSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['avatar_color', 'phone_number', 'email_signature']


class UserWithProfileSerializer(serializers.ModelSerializer):
    groups = GroupField(many=True, read_only=True)
    profile = ProfileSerializer(many=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'profile', 'groups', 'is_active')


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserWithGroupSerializer(many=False)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('user', 'avatar_url', 'phone_number', 'email_signature')

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url


class DocumentsSerializer(serializers.ModelSerializer):
    group_list = serializers.SerializerMethodField()

    class Meta:
        model = Documents
        fields = ('title', 'url', 'group_list')

    def get_group_list(self, obj):
        return obj.groups.all().values_list('name', flat=True)


class FunctionPermissionSerializer(serializers.ModelSerializer):
    module = FunctionModuleField(many=False, queryset=FunctionModule.objects.all())
    users = UserField(many=True, queryset=User.objects.all(), required=False)
    groups = GroupField(many=True, queryset=Group.objects.all(), required=False)
    groups_perms = serializers.SerializerMethodField()

    class Meta:
        model = FunctionPermission
        fields = '__all__'

    def get_groups_perms(self, obj):
        has_perm_groups = obj.groups.all().values_list('name', flat=True)
        groups = Group.objects.order_by('name')
        groups_perms_dict = {}
        for group in groups:
            groups_perms_dict[group.id] = {'name': group.name, 'id': group.id,
                                           'has_perm': True if group.name in has_perm_groups else False}
        return groups_perms_dict


class FunctionPermissionSimpleSerializer(serializers.ModelSerializer):
    module = FunctionModuleField(many=False, queryset=FunctionModule.objects.all())

    class Meta:
        model = FunctionPermission
        exclude = ['users', 'groups']


class GroupWithFunctionPermissionSerializer(serializers.ModelSerializer):
    func_perms = FunctionPermissionSerializer(read_only=True, many=True)

    class Meta:
        model = Group
        fields = '__all__'


class UserWithFunctionPermissionSerializer(serializers.ModelSerializer):
    func_perms = FunctionPermField(many=True, read_only=True)
    groups = GroupField(many=True, read_only=True)
    profile = ProfileSerializer(many=False)

    # cancelled_permissions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        exclude = ['password', 'user_permissions']

    # def get_cancelled_permissions(self, obj):
    #     return cache.get('user-{}-cancelled-permissions'.format(obj.id), [])


class UserFunctionPermListSerializer(serializers.ModelSerializer):
    func_perms = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'func_perms', 'is_active')

    def get_func_perms(self, obj):
        func_perms = get_user_function_perms(obj)
        func_perms_data = FunctionPermissionSimpleSerializer(func_perms, many=True).data
        return func_perms_data


class FunctionModuleWithPermissionSerializer(serializers.ModelSerializer):
    func_perms = serializers.SerializerMethodField()

    class Meta:
        model = FunctionModule
        fields = '__all__'

    def get_func_perms(self, obj):
        func_perms = obj.func_perms.order_by('name')
        return FunctionPermissionSerializer(func_perms, many=True).data


class FunctionModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FunctionModule
        fields = '__all__'


class CreateUserSerializer(serializers.ModelSerializer):
    groups = GroupField(many=True, queryset=Group.objects.all(), required=False)
    func_perms = FunctionPermField(many=True, queryset=FunctionPermission.objects.all(), required=False)
    password = serializers.CharField(required=False, write_only=True)
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = '__all__'

    def create(self, validated_data):
        user = super(CreateUserSerializer, self).create(validated_data)
        if validated_data.get('password', None):
            user.set_password(validated_data['password'])
            user.save()
        return user

    def update(self, instance, validated_data):
        user = super(CreateUserSerializer, self).update(instance, validated_data)
        if validated_data.get('password', None):
            user.set_password(validated_data['password'])
            user.save()
        return user


class FuncPermWithGroupSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()

    class Meta:
        model = FunctionPermission
        fields = ['name', 'codename', 'groups']

    def get_groups(self, obj):
        groups = obj.groups.all().values_list('name', flat=True)
        return groups


class FuncModuleWithPermsSerializer(serializers.ModelSerializer):
    func_perms = FuncPermWithGroupSerializer(read_only=True, many=True)
    func_module = serializers.SerializerMethodField()

    class Meta:
        model = FunctionModule
        fields = ['func_perms', 'func_module', 'name', 'codename']

    def get_func_module(self, obj):
        data = {'name': obj.name, 'codename': obj.codename}
        return data


class FuncPermInitSerializer(serializers.ModelSerializer):
    class Meta:
        model = FunctionPermission
        fields = ['name', 'codename']


class FuncPermInitWithGroupsSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()

    class Meta:
        model = FunctionPermission
        fields = ['name', 'codename', 'groups']

    def get_groups(self, obj):
        groups = obj.groups.all().values_list('name', flat=True)
        return groups


class FuncModuleInitSerializer(serializers.ModelSerializer):
    func_perms = FuncPermInitSerializer(read_only=True, many=True)
    func_module = serializers.SerializerMethodField()

    class Meta:
        model = FunctionModule
        fields = ['func_perms', 'func_module', 'name', 'codename']

    def get_func_module(self, obj):
        data = {'name': obj.name, 'codename': obj.codename}
        return data


class FuncModuleInitWithGroupsSerializer(serializers.ModelSerializer):
    func_perms = FuncPermInitWithGroupsSerializer(read_only=True, many=True)
    func_module = serializers.SerializerMethodField()

    class Meta:
        model = FunctionModule
        fields = ['func_perms', 'func_module', 'name', 'codename']

    def get_func_module(self, obj):
        data = {'name': obj.name, 'codename': obj.codename}
        return data


class UserWithGitlabUserSerializer(serializers.ModelSerializer):
    gitlab_user = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'gitlab_user', 'is_active')

    def get_gitlab_user(self, obj):
        if obj.profile and obj.profile.gitlab_user_id:
            return get_gitlab_user_simple_data(obj.profile.gitlab_user_id)


class TeamField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = Team.objects.get(pk=value.pk)
        dict = {"id": obj.pk, "name": obj.name}
        return dict


class TeamUserSerializer(serializers.ModelSerializer):
    team = TeamField(many=False, queryset=Team.objects.all())
    user = UserField(many=False, queryset=User.objects.all())

    class Meta:
        model = TeamUser
        fields = '__all__'


class TeamSerializer(serializers.ModelSerializer):
    leader = UserField(many=False, queryset=User.objects.all())
    team_users = TeamUserSerializer(many=True, read_only=True)
    members = UserField(many=True, read_only=True)

    class Meta:
        model = Team
        fields = '__all__'
