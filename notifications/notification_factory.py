from django.contrib.auth.models import User

from django.conf import settings

from notifications.utils import create_notification_to_users, create_notification, create_notification_group


class NotificationFactory(object):
    site_url = settings.SITE_URL

    @classmethod
    def build_job_contract_notifications(cls, obj, operator=None):
        '''
        工程师合同的消息推送
        :param obj:
        :param operator:
        :return:
        '''
        project = obj.project
        operator_username = operator.username if operator else ''
        if obj.contract_category == 'regular':
            url = cls.site_url + "/finance/developers/regular_contracts/?status={}&contract_id={}".format(obj.status,
                                                                                                          obj.id)
            legal_url = manager_url = url
        else:
            legal_url = cls.site_url + "/finance/developers/contracts/?status={}&contract_id={}".format(
                obj.status, obj.id)
            manager_url = cls.site_url + "/projects/detail/?projectId={}&anchor=roles".format(project.id)

        contract_full_name = "{project}工程师【{developer}】的合同【{contract}】".format(
            project="项目【{}】的".format(obj.project.name) if obj.project else '固定',
            developer=obj.developer.name,
            contract=obj.contract_name
        )
        if obj.status == 'un_generate':
            content = "{contract}已提交，请完善合同信息并发给工程师确认".format(contract=contract_full_name)
        elif obj.status == 'rejected':
            content = "{contract}被【{operator}】驳回，请重新修改后提交".format(contract=contract_full_name,
                                                                  operator=operator_username)
        elif obj.status == 'signed':
            content = "{contract}已签约".format(contract=contract_full_name)
        elif obj.status == 'closed':
            content = "{contract}被【{operator}】关闭，关闭原因：【{reason}】".format(contract=contract_full_name,
                                                                         operator=operator_username,
                                                                         reason=obj.close_reason)
        else:
            return
        legal_personnel = User.objects.filter(username__in=settings.LEGAL_PERSONNEL, is_active=True)
        if operator:
            legal_personnel = legal_personnel.exclude(pk=operator.id)
        contract_manager = obj.manager

        if legal_personnel:
            create_notification_to_users(legal_personnel, content, legal_url, is_important=True)
        if contract_manager:
            if operator and contract_manager.id == operator.id:
                return
            create_notification(contract_manager, content, manager_url, is_important=True)

    @classmethod
    def build_job_payment_notifications(cls, obj, operator):
        payment = obj
        project = obj.project
        developer = obj.developer
        job_contract = obj.job_contract
        manager = payment.manager
        new_status = obj.status

        # 财务的链接   负责人的链接
        finance_url = cls.site_url + '/finance/developers/payments/'
        if project:
            manager_url = cls.site_url + "/projects/detail/?projectId={}&anchor=roles".format(project.id)
        elif job_contract and job_contract.contract_category == 'regular':
            manager_url = cls.site_url + "/finance/developers/regular_contracts/?status={}&contract_id={}".format(
                job_contract.status,
                job_contract.id)
        else:
            manager_url = ''
        content = "{project}工程师【{developer}】{contract}的一笔打款{status_display}，金额：【{amount}】".format(
            project="项目【{}】的".format(project.name) if project else '固定',
            developer=developer.name,
            contract='合同【{contract}】'.format(contract=job_contract.contract_name) if job_contract else '',
            status_display=payment.status_display,
            amount=payment.amount
        )
        if new_status == 1:
            create_notification_group(settings.GROUP_NAME_DICT["finance"], content,
                                      url=finance_url)
        else:
            if manager and operator.id != manager.id:
                create_notification(manager, content, manager_url)

    @classmethod
    def build_comment_notifications(cls, obj, operator):
        '''
        评论的消息推送
        :param obj:
        :param operator:
        :return:
        '''
        content_type = obj.content_type
        content_text = obj.clean_content()
        if content_type:
            # 工程师打款项-评论
            if content_type.model == 'jobpayment':
                payment = obj.content_object
                project = payment.project
                manager = payment.manager
                developer = payment.developer
                job_contract = payment.job_contract

                # 财务的链接   负责人的链接
                finance_url = cls.site_url + '/finance/developers/payments/'
                if project:
                    manager_url = cls.site_url + "/projects/detail/?projectId={}&anchor=roles".format(project.id)
                elif job_contract and job_contract.contract_category == 'regular':
                    manager_url = cls.site_url + "/finance/developers/regular_contracts/?status={}&contract_id={}".format(
                        job_contract.status,
                        job_contract.id)
                else:
                    manager_url = ''
                content = "{project}工程师【{developer}】{contract}的一笔打款收到一条评论：{content}".format(
                    project="项目【{}】的".format(project.name) if project else '固定',
                    developer=developer.name,
                    contract='合同【{contract}】'.format(contract=job_contract.contract_name) if job_contract else '',
                    content=content_text
                )
                # 如果是财务评论的，推送项目经理；如果不是财务评论的推送给全部财务人员
                if operator.groups.filter(name=settings.GROUP_NAME_DICT["finance"]).exists():
                    if manager and operator.id != manager.id:
                        create_notification(manager, content, manager_url)
                else:
                    create_notification_group(settings.GROUP_NAME_DICT["finance"], content,
                                              url=finance_url)
