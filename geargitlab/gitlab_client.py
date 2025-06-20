# -*- coding:utf-8 -*-
from datetime import datetime, timedelta
from copy import deepcopy
import json
import re
from pprint import pprint
import logging
from base64 import b64decode, b64encode

from django.conf import settings
from django.utils.http import urlquote
import requests
import gitlab

logger = logging.getLogger()


class GitlabClient(object):
    def __init__(self, admin_token=None, private_token=None, base_url=None):
        """Constructs a GitlabClient API client.
        If `access_token` is given, all of the API methods in the client
        will work to read and modify GitlabClient documents.

        Otherwise, only `get_authorization_url` and `get_access_token`
        work, and we assume the client is for a server using the GitlabClient API's
        OAuth endpoint.
        """
        self.admin_private_token = admin_token if admin_token else settings.GITLAB_ADMIN_PRIVATE_TOKEN
        self.private_token = private_token
        self.base_url = base_url if base_url else "https://git.chilunyc.com"
        self.admin_client = gitlab.Gitlab(self.base_url, private_token=self.admin_private_token)
        self.user_client = gitlab.Gitlab(self.base_url, private_token=self.private_token) if private_token else None

    def successful_result(self, data=None, message='Successful'):
        return {'result': True, 'message': message, 'data': data}

    def failed_result(self, data=None, message='Failed'):
        return {'result': False, 'message': message, 'data': data}

    def get_all_users(self):
        return self.admin_client.users.list(all=True)

    def get_all_blocked_users(self):
        return self.admin_client.users.list(all=True, blocked=True)

    def get_all_active_users(self):
        return self.admin_client.users.list(all=True, active=True)

    def get_active_users(self, created_before=None, created_after=None, today=False):
        if today:
            now = datetime.now()
            created_before = now
            created_after = datetime(now.year, now.month, now.day, 0, 0, 0)
        if created_after:
            created_after = created_after - timedelta(hours=8)
        if created_before:
            created_before = created_before - timedelta(hours=8)

        return self.admin_client.users.list(all=True, active=True, created_after=created_after,
                                            created_before=created_before)

    def get_user(self, username=None, user_id=None):
        '''
        :param username:
        :param user_id:
        :return:
        <class 'gitlab.v4.objects.User'> =>
        {'id': 217, 'name': 'lifanpingtest', 'username': 'lifanpingtest', 'state': 'active', 'avatar_url': 'https://secure.gravatar.com/avatar/732f74a8e36344935e739fdcbca3f811?s=80&d=identicon', 'web_url': 'https://git.chilunyc.com/lifanpingtest', 'created_at': '2019-07-28T15:46:38.869Z', 'bio': None, 'location': None, 'public_email': '', 'skype': '', 'linkedin': '', 'twitter': '', 'website_url': '', 'organization': None, 'last_sign_in_at': '2019-07-28T15:47:37.467Z', 'confirmed_at': '2019-07-28T15:47:00.197Z', 'last_activity_on': '2019-07-29', 'email': 'xingjiantianzi@qq.com', 'theme_id': 1, 'color_scheme_id': 1, 'projects_limit': 0, 'current_sign_in_at': '2019-07-28T15:47:37.467Z', 'identities': [], 'can_create_group': False, 'can_create_project': False, 'two_factor_enabled': False, 'external': True, 'private_profile': None, 'is_admin': False}
        '''
        if username:
            user = self.admin_client.users.list(username=username)
            if user:
                return user[0]
        elif user_id:
            try:
                user = self.admin_client.users.get(user_id)
                return user
            except:
                pass

    def block_user(self, username=None, user_id=None):
        user = self.get_user(username=username, user_id=user_id)
        if user:
            user.block()
            return True

    def unblock_user(self, username=None, user_id=None):
        user = self.get_user(username=username, user_id=user_id)
        if user:
            user.unblock()
            return True

    def create_user_token(self, user=None, username=None, user_id=None):
        '''

        :param user:
        :param username:
        :param user_id:
        :return:
        <class 'gitlab.v4.objects.UserImpersonationToken'> =>
        {'id': 143, 'name': 'farm_token', 'revoked': False, 'created_at': '2019-07-29T04:01:19.230Z', 'scopes': ['api'], 'active': True, 'expires_at': None, 'token': 'mnMs2VjNsrUaKDXt-QmG', 'impersonation': True}
        '''
        if not user:
            user = self.get_user(username=username, user_id=user_id)
        if user:
            token = user.impersonationtokens.create({'name': 'farm_token', 'scopes': ['api']})
            return token

    def get_user_token(self, user=None, username=None, user_id=None, token_id=None):
        '''

        :param user:
        :param username:
        :param user_id:
        :param token_id:
        :return:
        <class 'gitlab.v4.objects.UserImpersonationToken'> =>
        {'id': 141, 'name': 'farm_token', 'revoked': False, 'created_at': '2019-07-29T03:55:44.680Z', 'scopes': ['api'], 'active': True, 'expires_at': None, 'impersonation': True}
        '''
        if not user:
            user = self.get_user(username=username, user_id=user_id)
        if user:
            if token_id:
                return user.impersonationtokens.get(token_id)

    def get_user_tokens(self, user=None, username=None, user_id=None):
        if not user:
            user = self.get_user(username=username, user_id=user_id)
        if user:
            return user.impersonationtokens.list(state='active')

    def get_all_projects(self):
        return self.admin_client.projects.list(all=True)

    def get_projects(self, per_page=20, order_by='created_at', sort='desc'):
        return self.admin_client.projects.list(order_by=order_by, sort=sort, per_page=per_page)

    def get_user_projects(self, private_token=None):
        user_client = self.user_client
        if private_token:
            user_client = gitlab.Gitlab(self.base_url, private_token=private_token)
        if user_client:
            user_projects = user_client.projects.list(all=True, membership=True)
            return user_projects

    def get_user_projects_groups(self, private_token=None):
        user_client = self.user_client
        if private_token:
            user_client = gitlab.Gitlab(self.base_url, private_token=private_token)
        if user_client:
            user_projects = user_client.projects.list(all=True, membership=True)
            user_groups = user_client.groups.list(all_available=False, membership=True)
            return (user_projects, user_groups)

    def get_project(self, project_id=None):
        '''
        :param project_id:
        :return:
        <class 'gitlab.v4.objects.Project'> =>
        {'id': 673, 'description': '', 'name': 'lifanping-test-demo', 'name_with_namespace': 'lifanping / lifanping-test-demo', 'path': 'lifanping-test-demo', 'path_with_namespace': 'lifanping/lifanping-test-demo', 'created_at': '2019-07-26T10:51:08.826Z', 'default_branch': None, 'tag_list': [], 'ssh_url_to_repo': 'git@git.chilunyc.com:lifanping/lifanping-test-demo.git', 'http_url_to_repo': 'https://git.chilunyc.com/lifanping/lifanping-test-demo.git', 'web_url': 'https://git.chilunyc.com/lifanping/lifanping-test-demo', 'readme_url': None, 'avatar_url': None, 'star_count': 0, 'forks_count': 0, 'last_activity_at': '2019-07-29T04:13:58.500Z', 'namespace': {'id': 190, 'name': 'lifanping', 'path': 'lifanping', 'kind': 'user', 'full_path': 'lifanping', 'parent_id': None}, '_links': {'self': 'https://git.chilunyc.com/api/v4/projects/673', 'issues': 'https://git.chilunyc.com/api/v4/projects/673/issues', 'merge_requests': 'https://git.chilunyc.com/api/v4/projects/673/merge_requests', 'repo_branches': 'https://git.chilunyc.com/api/v4/projects/673/repository/branches', 'labels': 'https://git.chilunyc.com/api/v4/projects/673/labels', 'events': 'https://git.chilunyc.com/api/v4/projects/673/events', 'members': 'https://git.chilunyc.com/api/v4/projects/673/members'}, 'archived': False, 'visibility': 'internal', 'owner': {'id': 111, 'name': 'lifanping', 'username': 'lifanping', 'state': 'active', 'avatar_url': 'https://git.chilunyc.com/uploads/-/system/user/avatar/111/avatar.png', 'web_url': 'https://git.chilunyc.com/lifanping'}, 'resolve_outdated_diff_discussions': False, 'container_registry_enabled': True, 'issues_enabled': True, 'merge_requests_enabled': True, 'wiki_enabled': True, 'jobs_enabled': True, 'snippets_enabled': True, 'shared_runners_enabled': True, 'lfs_enabled': True, 'creator_id': 111, 'import_status': 'none', 'import_error': None, 'open_issues_count': 0, 'runners_token': 'yHG5pKHzfj3s4zs3kxBZ', 'public_jobs': True, 'ci_config_path': None, 'shared_with_groups': [], 'only_allow_merge_if_pipeline_succeeds': False, 'request_access_enabled': False, 'only_allow_merge_if_all_discussions_are_resolved': False, 'printing_merge_request_link_enabled': True, 'merge_method': 'merge', 'external_authorization_classification_label': None, 'permissions': {'project_access': {'access_level': 40, 'notification_level': 3}, 'group_access': None}}
        '''
        if project_id:
            try:
                return self.admin_client.projects.get(project_id)
            except Exception as e:
                logger.error(e)
                pass

    def get_project_members(self, project_id=None):
        '''
        :param project_id:
        :return:
        [<class 'gitlab.v4.objects.ProjectMember'> => {'id': 111, 'name': 'lifanping', 'username': 'lifanping', 'state': 'active', 'avatar_url': 'https://git.chilunyc.com/uploads/-/system/user/avatar/111/avatar.png', 'web_url': 'https://git.chilunyc.com/lifanping', 'access_level': 50, 'expires_at': None}
        ,...]
        '''
        if project_id:
            return self.admin_client.projects.get(project_id).members.all(all=True)

    def delete_project_members(self, project_id=None, user=None, username=None, user_id=None):
        if not user:
            user = self.get_user(username=username, user_id=user_id)
        if project_id and user:
            self.admin_client.projects.get(project_id).members.delete(user.id)
            return True

    def get_all_groups(self):
        return self.admin_client.groups.list(all=True)

    def get_groups(self, per_page=20, order_by='id', sort='desc'):
        return self.admin_client.groups.list(order_by=order_by, sort=sort, per_page=per_page)

    def get_user_groups(self, private_token=None):
        user_client = self.user_client
        if private_token:
            user_client = gitlab.Gitlab(self.base_url, private_token=private_token)
        if user_client:
            user_groups = user_client.groups.list(all_available=False, membership=True)
            return user_groups

    def get_group(self, group_id):
        '''
        :param group_id:
        :return:
        <class 'gitlab.v4.objects.Group'> =>
        {'id': 396, 'web_url': 'https://git.chilunyc.com/groups/lifanpingtestgrouo', 'name': 'lifanpingtestgrouo', 'path': 'lifanpingtestgrouo', 'description': '', 'visibility': 'private', 'lfs_enabled': True, 'avatar_url': None, 'request_access_enabled': False, 'full_name': 'lifanpingtestgrouo', 'full_path': 'lifanpingtestgrouo', 'parent_id': None, 'projects': [{'id': 674, 'description': '', 'name': 'lifanpingtest', 'name_with_namespace': 'lifanpingtestgrouo / lifanpingtest', 'path': 'lifanpingtest', 'path_with_namespace': 'lifanpingtestgrouo/lifanpingtest', 'created_at': '2019-07-29T04:34:12.493Z', 'default_branch': None, 'tag_list': [], 'ssh_url_to_repo': 'git@git.chilunyc.com:lifanpingtestgrouo/lifanpingtest.git', 'http_url_to_repo': 'https://git.chilunyc.com/lifanpingtestgrouo/lifanpingtest.git', 'web_url': 'https://git.chilunyc.com/lifanpingtestgrouo/lifanpingtest', 'readme_url': None, 'avatar_url': None, 'star_count': 0, 'forks_count': 0, 'last_activity_at': '2019-07-29T04:34:12.493Z', 'namespace': {'id': 396, 'name': 'lifanpingtestgrouo', 'path': 'lifanpingtestgrouo', 'kind': 'group', 'full_path': 'lifanpingtestgrouo', 'parent_id': None}, '_links': {'self': 'https://git.chilunyc.com/api/v4/projects/674', 'issues': 'https://git.chilunyc.com/api/v4/projects/674/issues', 'merge_requests': 'https://git.chilunyc.com/api/v4/projects/674/merge_requests', 'repo_branches': 'https://git.chilunyc.com/api/v4/projects/674/repository/branches', 'labels': 'https://git.chilunyc.com/api/v4/projects/674/labels', 'events': 'https://git.chilunyc.com/api/v4/projects/674/events', 'members': 'https://git.chilunyc.com/api/v4/projects/674/members'}, 'archived': False, 'visibility': 'private', 'resolve_outdated_diff_discussions': False, 'container_registry_enabled': True, 'issues_enabled': True, 'merge_requests_enabled': True, 'wiki_enabled': True, 'jobs_enabled': True, 'snippets_enabled': True, 'shared_runners_enabled': True, 'lfs_enabled': True, 'creator_id': 111, 'import_status': 'none', 'open_issues_count': 0, 'public_jobs': True, 'ci_config_path': None, 'shared_with_groups': [], 'only_allow_merge_if_pipeline_succeeds': False, 'request_access_enabled': False, 'only_allow_merge_if_all_discussions_are_resolved': False, 'printing_merge_request_link_enabled': True, 'merge_method': 'merge', 'external_authorization_classification_label': None}], 'shared_projects': []}
        '''
        if group_id:
            try:
                return self.admin_client.groups.get(group_id)
            except Exception as e:
                logger.error(e)
                pass

    def get_group_members(self, group_id=None):
        '''
        :param project_id:
        :return:
        [<class 'gitlab.v4.objects.ProjectMember'> => {'id': 111, 'name': 'lifanping', 'username': 'lifanping', 'state': 'active', 'avatar_url': 'https://git.chilunyc.com/uploads/-/system/user/avatar/111/avatar.png', 'web_url': 'https://git.chilunyc.com/lifanping', 'access_level': 50, 'expires_at': None}
        ,...]
        '''
        if group_id:
            return self.admin_client.groups.get(group_id).members.all(all=True)

    def delete_group_members(self, group_id=None, user=None, username=None, user_id=None):
        if not user:
            user = self.get_user(username=username, user_id=user_id)
        if group_id and user:
            self.admin_client.groups.get(group_id).members.delete(user.id)
            return True

    def get_project_branches(self, project=None, project_id=None):
        branches = []
        if not project and project_id:
            project = self.get_project(project_id)
        if project:
            branches = project.branches.list(all=True)
        return branches

    def get_group_commits(self, group=None, group_id=None, start_time=None, end_time=None, today=True,
                          is_all=True, ref_name=None, with_stats=True):
        commits = []
        if not group and group_id:
            group = self.get_group(group_id)
        if group:
            for project in group.projects.list(all=True, include_subgroups=True):
                project_commits = self.get_project_commits(project_id=project.id, start_time=start_time,
                                                           end_time=end_time, today=today, is_all=is_all,
                                                           ref_name=ref_name,
                                                           with_stats=with_stats)
                if project_commits:
                    commits.extend(project_commits)
        return commits

    def get_group_commits_data(self, group=None, group_id=None, start_time=None, end_time=None, today=True,
                               is_all=True, ref_name=None, with_stats=True):
        commits = []
        if not group and group_id:
            group = self.get_group(group_id)
        if group:
            for project in group.projects.list(all=True, include_subgroups=True):
                project_commits = self.get_project_commits(project_id=project.id, start_time=start_time,
                                                           end_time=end_time, today=today, is_all=is_all,
                                                           ref_name=ref_name,
                                                           with_stats=with_stats)
                if project_commits:
                    commits.extend(project_commits)
        return [commit.attributes for commit in commits]

    def get_project_commits(self, project=None, project_id=None, start_time=None, end_time=None, today=True,
                            is_all=True, ref_name=None, with_stats=True):
        '''
        :param project:
        :param project_id:
        :param start_time:
        :param end_time:
        :param today:
        :param is_all:
        :param ref_name:
        :param with_stats:
        :return:
        '''
        commits = []
        if not project and project_id:
            project = self.get_project(project_id)
        if project:
            # 默认获取当天数据
            since = None
            until = None
            now = datetime.now()
            if not start_time and today:
                today_zero = datetime(now.year, now.month, now.day, 0, 0, 0)
                start_time = today_zero
            if not end_time and today:
                end_time = now

            if start_time:
                since = start_time - timedelta(hours=8)
            if end_time:
                until = end_time - timedelta(hours=8)
            commits = project.commits.list(since=since, until=until, all=is_all, ref_name=ref_name,
                                           with_stats=with_stats)
        return commits

    def get_project_commits_data(self, project=None, project_id=None, start_time=None, end_time=None, today=True,
                                 is_all=True, ref_name=None, with_stats=True):
        '''
        :param project:
        :param project_id:
        :param start_time:
        :param end_time:
        :param today:
        :param is_all:
        :param ref_name:
        :param with_stats:
        :return:
        [{'author_email': 'fanping@chilunyc.com',
          'author_name': 'fanping',
          'authored_date': '2019-09-04T03:30:51.000Z',
          'committed_date': '2019-09-04T03:30:51.000Z',
          'committer_email': 'fanping@chilunyc.com',
          'committer_name': 'fanping',
          'created_at': '2019-09-04T03:30:51.000Z',
          'id': 'f4a2ed8f783ee5ca0613bb8cd8107f2267e38062',
          'message': '工单列表\n',
          'parent_ids': ['212ccb4844cf132c4b37fad430be81388df12ca2'],
          'project_id': 36,
          'short_id': 'f4a2ed8f',
          'title': '工单列表'}]
        '''

        commits = self.get_project_commits(project=project, project_id=project_id, start_time=start_time,
                                           end_time=end_time, today=today, is_all=is_all, ref_name=ref_name,
                                           with_stats=with_stats)
        return [commit.attributes for commit in commits]

    def get_project_day_commits_data(self, day, project=None, project_id=None):
        new_data = {}
        if not project and project_id:
            project = self.get_project(project_id)
        if project:
            branches = project.branches.list(all=True)
            for branch in branches:
                branch_name = branch.name
                # 判断该分支最近一次commit是否在今天
                last_commit = branch.commit
                if last_commit:
                    day_zero = datetime(day.year, day.month, day.day, 0, 0, 0)
                    day_end = datetime(day.year, day.month, day.day, 23, 59, 59)
                    committed_date = None
                    try:
                        if '+08:00' in last_commit['committed_date']:
                            committed_date = datetime.strptime(last_commit['committed_date'],
                                                               "%Y-%m-%dT%H:%M:%S.%f+08:00")
                        elif last_commit['committed_date'].endswith('Z'):
                            committed_date = datetime.strptime(last_commit['committed_date'],
                                                               "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(
                                hours=8)
                    except Exception as e:
                        logger.info(last_commit)
                        logger.info(e)
                    if committed_date and committed_date < day_zero:
                        continue
                    commits_data = self.get_project_commits_data(project=project, today=False,
                                                                 start_time=day_zero,
                                                                 end_time=day_end,
                                                                 ref_name=branch_name)
                    for commit_data in commits_data:
                        short_id = commit_data['short_id']
                        new_data[short_id] = commit_data
        return new_data

    def get_project_day_issues_data(self, day, project=None, project_id=None):
        if not project and project_id:
            project = self.get_project(project_id)
        if project:
            day_zero = datetime(day.year, day.month, day.day, 0, 0, 0)
            day_end = datetime(day.year, day.month, day.day, 23, 59, 59)
            return self.get_project_issues_data(project=project, start_time=day_zero, end_time=day_end)

    def get_project_issues_data(self, project=None, project_id=None, start_time=None, end_time=None):
        if not project and project_id:
            project = self.get_project(project_id)
        if project:
            opened_issues = self.get_project_created_issues_data(project, start_time=start_time, end_time=end_time)
            closed_issues = self.get_project_closed_issues_data(project, start_time=start_time, end_time=end_time)
            if opened_issues or closed_issues:
                return {"opened_issues": opened_issues, "closed_issues": closed_issues}

    def get_project_created_issues_data(self, project, start_time=None, end_time=None):
        '''
        :param project:
        :param start_time:
        :param end_time:
        :return:
        [
            {
                'id': 14102, 'iid': 41, 'project_id': 36, 'title': '爬虫数量测试', 'description': '爬虫数量测试', 'state': 'closed',
                'created_at': '2019-10-10T14:22:36.499Z', 'updated_at': '2019-10-10T14:49:26.265Z',
                'closed_at': '2019-10-10T14:49:26.255Z',
                'closed_by': {'id': 111, 'name': 'hahaha', 'username': 'lifanping', 'state': 'active',
                              'avatar_url': 'https://git.chilunyc.com/uploads/-/system/user/avatar/111/avatar.png',
                              'web_url': 'https://git.chilunyc.com/lifanping'}, 'labels': [], 'milestone': None,
                'assignees': [],
                'author': {'id': 111, 'name': 'hahaha', 'username': 'lifanping', 'state': 'active',
                           'avatar_url': 'https://git.chilunyc.com/uploads/-/system/user/avatar/111/avatar.png',
                           'web_url': 'https://git.chilunyc.com/lifanping'}, 'assignee': None, 'user_notes_count': 0,
                'merge_requests_count': 0, 'upvotes': 0, 'downvotes': 0, 'due_date': None, 'confidential': False,
                'discussion_locked': None, 'web_url': 'https://git.chilunyc.com/chaoneng/GearFarm/issues/41',
                'time_stats': {'time_estimate': 0, 'total_time_spent': 0, 'human_time_estimate': None,
                               'human_total_time_spent': None}
            }
        ]=>
         [
            {
                'id': 14102, '
                'title': '爬虫数量测试',
                'state': 'closed',
                'created_at': '2019-10-10T14:22:36.499Z',
                'closed_at': '2019-10-10T14:49:26.255Z',
                'closed_by': {'id': 111,  'username': 'lifanping'}
                'author': {'id': 111, 'username': 'lifanping'}
            }
        ]
        '''
        if start_time:
            start_time = start_time - timedelta(hours=8)
        if end_time:
            end_time = end_time - timedelta(hours=8)
        issues = project.issues.list(created_after=start_time, created_before=end_time, all=True)
        # issue_list = [issue.attributes for issue in issues]
        issues_data = []
        for issue in issues:
            issue_data = self._get_issue_data(issue)
            issues_data.append(issue_data)
        return issues_data

    def get_project_opened_issues_data(self, project=None, project_id=None, start_time=None, end_time=None):
        '''
        :param project:
        :param start_time:
        :param end_time:
        :return:
        [
            {
                'id': 14102, 'iid': 41, 'project_id': 36, 'title': '爬虫数量测试', 'description': '爬虫数量测试', 'state': 'opened',
                'created_at': '2019-10-10T14:22:36.499Z', 'updated_at': '2019-10-10T14:49:26.265Z',
                'closed_at': None,
                'closed_by': {'id': 111, 'name': 'hahaha', 'username': 'lifanping', 'state': 'active',
                              'avatar_url': 'https://git.chilunyc.com/uploads/-/system/user/avatar/111/avatar.png',
                              'web_url': 'https://git.chilunyc.com/lifanping'}, 'labels': [], 'milestone': None,
                'assignees': [],
                'author': {'id': 111, 'name': 'hahaha', 'username': 'lifanping', 'state': 'active',
                           'avatar_url': 'https://git.chilunyc.com/uploads/-/system/user/avatar/111/avatar.png',
                           'web_url': 'https://git.chilunyc.com/lifanping'}, 'assignee': None, 'user_notes_count': 0,
                'merge_requests_count': 0, 'upvotes': 0, 'downvotes': 0, 'due_date': None, 'confidential': False,
                'discussion_locked': None, 'web_url': 'https://git.chilunyc.com/chaoneng/GearFarm/issues/41',
                'time_stats': {'time_estimate': 0, 'total_time_spent': 0, 'human_time_estimate': None,
                               'human_total_time_spent': None}
            }
        ]=>
         [
            {
                'id': 14102, '
                'title': '爬虫数量测试',
                'assignees': [{'id': 111,'username': 'lifanping'}],
                'created_at': '2019-10-10T14:22:36.499Z',
                'author': {'id': 111, 'username': 'lifanping'}
            }
        ]
        '''
        if not project and project_id:
            project = self.get_project(project_id)
        if not project:
            return
        if start_time:
            start_time = start_time - timedelta(hours=8)
        if end_time:
            end_time = end_time - timedelta(hours=8)
        issues = project.issues.list(created_after=start_time, created_before=end_time, state="opened", all=True)
        # issue_list = [issue.attributes for issue in issues]
        issues_data = []
        for issue in issues:
            issue_data = self._get_issue_data(issue)
            issues_data.append(issue_data)
        return issues_data

    def _get_issue_data(self, issue, with_assignees=True):
        attribute = issue.attributes
        closed_by = attribute['closed_by']
        author = attribute['author']
        issue_data = {
            'id': attribute['id'],
            'title': attribute['title'],
            'state': attribute['state'],
            'project_id': attribute.get('project_id'),
            'created_at': attribute['created_at'],
            'closed_at': attribute['closed_at'],
            'closed_by': {"id": closed_by['id'],
                          "username": closed_by['username']} if closed_by else None,
            'author': {"id": author['id'], "username": author['username']} if author else None,
        }
        if with_assignees:
            issue_data['assignees'] = [{"id": author['id'], "username": author['username']} for author in
                                       attribute['assignees']]

        return issue_data

    # def _get_issue_data(self, issue, project_id=None):
    #     attribute = issue.attributes
    #     author = attribute['author']
    #     issue_data = {
    #         'id': attribute['id'],
    #         'created_at': attribute['created_at'],
    #         'project_id': attribute.get('project_id') or project_id,
    #         'assignees': [{"id": author['id'], "username": author['username']} for author in attribute['assignees']],
    #         'author': {"id": author['id'], "username": author['username']} if author else None,
    #     }
    #     return issue_data

    def get_project_closed_issues_data(self, project, start_time=None, end_time=None):
        if start_time:
            start_time = start_time - timedelta(hours=8)
        if end_time:
            end_time = end_time - timedelta(hours=8)
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if start_time else None
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if end_time else None
        issues = project.issues.list(updated_after=start_time, updated_before=end_time, state="closed", all=True)
        # issues_data = [issue.attributes for issue in issues]
        issues_data = []
        for issue in issues:
            issue_data = self._get_issue_data(issue)
            closed_at = issue_data['closed_at']
            if start_str and end_str:
                if start_str <= closed_at <= end_str:
                    issues_data.append(issue_data)
            elif start_str:
                if start_str <= closed_at:
                    issues_data.append(issue_data)
            elif end_str:
                if closed_at <= end_str:
                    issues_data.append(issue_data)
            else:
                issues_data.append(issue_data)
        return issues_data

    def get_group_day_issues_data(self, day, group=None, group_id=None):
        if not group and group_id:
            group = self.get_group(group_id)
        if group:
            day_zero = datetime(day.year, day.month, day.day, 0, 0, 0)
            day_end = datetime(day.year, day.month, day.day, 23, 59, 59)
            print(day_zero, day_end)
            return self.get_group_issues_data(group=group, start_time=day_zero, end_time=day_end)

    def get_group_issues_data(self, group=None, group_id=None, start_time=None, end_time=None):
        if not group and group_id:
            group = self.get_group(group_id)
        if group:
            opened_issues = self.get_group_created_issues_data(group, start_time=start_time, end_time=end_time)
            closed_issues = self.get_group_closed_issues_data(group, start_time=start_time, end_time=end_time)
            if opened_issues or closed_issues:
                return {"opened_issues": opened_issues, "closed_issues": closed_issues}

    def get_group_created_issues_data(self, group, start_time=None, end_time=None):
        if start_time:
            start_time = start_time - timedelta(hours=8)
        if end_time:
            end_time = end_time - timedelta(hours=8)
        issues = group.issues.list(created_after=start_time, created_before=end_time, all=True)
        # issue_list = [issue.attributes for issue in issues]
        issues_data = []
        for issue in issues:
            issue_data = self._get_issue_data(issue)
            issues_data.append(issue_data)
        return issues_data

    def get_group_closed_issues_data(self, group, start_time=None, end_time=None):
        if start_time:
            start_time = start_time - timedelta(hours=8)
        if end_time:
            end_time = end_time - timedelta(hours=8)
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if start_time else None
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if end_time else None
        issues = group.issues.list(updated_after=start_time, updated_before=end_time, state="closed", all=True)
        # issues_data = [issue.attributes for issue in issues]
        issues_data = []
        for issue in issues:
            issue_data = self._get_issue_data(issue)
            closed_at = issue_data['closed_at']
            if start_str and end_str:
                if start_str <= closed_at <= end_str:
                    issues_data.append(issue_data)
            elif start_str:
                if start_str <= closed_at:
                    issues_data.append(issue_data)
            elif end_str:
                if closed_at <= end_str:
                    issues_data.append(issue_data)
            else:
                issues_data.append(issue_data)
        return issues_data

    def get_group_opened_issues_data(self, group=None, group_id=None, start_time=None, end_time=None):
        '''
        :param group:
        :param start_time:
        :param end_time:
        :return:
        [
            {'assignee': {'avatar_url': 'https://git.chilunyc.com/uploads/-/system/user/avatar/111/avatar.png',
                          'id': 111,
                          'name': 'hahaha',
                          'state': 'active',
                          'username': 'lifanping',
                          'web_url': 'https://git.chilunyc.com/lifanping'},
             'assignees': [{'avatar_url': 'https://git.chilunyc.com/uploads/-/system/user/avatar/111/avatar.png',
                            'id': 111,
                            'name': 'hahaha',
                            'state': 'active',
                            'username': 'lifanping',
                            'web_url': 'https://git.chilunyc.com/lifanping'}],
             'author': {'avatar_url': 'https://git.chilunyc.com/uploads/-/system/user/avatar/56/avatar.png',
                        'id': 56,
                        'name': 'Haipeng Tang',
                        'state': 'active',
                        'username': '949498490',
                        'web_url': 'https://git.chilunyc.com/949498490'},
             'closed_at': None,
             'closed_by': None,
             'confidential': False,
             'created_at': '2018-03-28T07:42:13.769Z',
             'description': '',
             'discussion_locked': None,
             'downvotes': 0,
             'due_date': None,
             'group_id': 198,
             'id': 1079,
             'iid': 205,
             'labels': ['P0', '修复finish'],
             'merge_requests_count': 0,
             'milestone': None,
             'project_id': 282,
             'state': 'opened',
             'time_stats': {'human_time_estimate': None,
                            'human_total_time_spent': None,
                            'time_estimate': 0,
                            'total_time_spent': 0},
             'title': '发电量推送短信的时间存在问题，目前日发电量是每天早上推送，与文案设计中的“今天”存在冲突',
             'updated_at': '2018-03-29T14:47:44.809Z',
             'upvotes': 0,
             'user_notes_count': 0,
             'web_url': 'https://git.chilunyc.com/xiaosolar/backend_new/issues/205'}
        ]=>
         [
            {
                'id': 14102,
                'title': '爬虫数量测试',
                'state': 'closed',
                'peoject_id': 282,
                'created_at': '2019-10-10T14:22:36.499Z',
                'closed_at': '2019-10-10T14:49:26.255Z',
                'closed_by': {'id': 111, 'username': 'lifanping'}
                'assignees': [{'id': 111, 'username': 'lifanping'}],
                'author': {'id': 111, 'username': 'lifanping'}
            }
        ]
        '''
        if not group and group_id:
            group = self.get_group(group_id)
        if not group:
            return
        if start_time:
            start_time = start_time - timedelta(hours=8)
        if end_time:
            end_time = end_time - timedelta(hours=8)
        issues = group.issues.list(created_after=start_time, created_before=end_time, state="opened", all=True)
        # issue_list = [issue.attributes for issue in issues]
        issues_data = []
        for issue in issues:
            issue_data = self._get_issue_data(issue)
            issues_data.append(issue_data)
        return issues_data


class GitlabOauthClient(object):
    def __init__(self, client_id=None, client_secret=None, base_url=None):
        self.base_url = base_url if base_url else "https://git.chilunyc.com"
        self.client_id = client_id if client_id else settings.GITLAB_FARM_CLIENT_ID
        self.client_secret = client_secret if client_secret else settings.GITLAB_FARM_CLIENT_SECRET
        self.oauth_url_temp = "{base_url}/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope=read_user+api"
        self.token_url = self.base_url + '/oauth/token'
        self.user_url = self.base_url + '/api/v4/user'

    def get_oauth_url(self, redirect_uri):
        redirect_uri = urlquote(redirect_uri)
        return self.oauth_url_temp.format(base_url=self.base_url, client_id=self.client_id, redirect_uri=redirect_uri)

    def get_access_token(self, code, redirect_uri):
        token_url = self.token_url
        request_data = {"client_id": self.client_id, "client_secret": self.client_secret, 'code': code,
                        "grant_type": "authorization_code", 'redirect_uri': redirect_uri}
        response = requests.post(token_url, request_data)
        if response.status_code == 200:
            response_data = response.json()
            access_token = response_data.get('access_token')
            return access_token

    def get_user_data(self, access_token):
        user_url = self.user_url
        params = {'access_token': access_token}
        response = requests.get(user_url, params=params)
        if response.status_code == 200:
            return response.json()





# client = GitlabClient()
# p = client.get_project(1131)
# # print(p.attributes, type(p.attributes))
#
# with open('test.json', 'w') as f:
#     f.write(json.dumps(p.attributes, ensure_ascii=False))