from django.test import TestCase

# Create your tests here.
import gitlab
gl = gitlab.Gitlab('https://git.chilunyc.com', private_token='3bye-YrM8Qp_St5o2MhS')

# projects = gl.projects.list(all=True, membership=True)
# print(len(projects))
# # for project in projects:
# #     print(project)


alice = gl.users.list(username='lifanping')[0]
projects = alice.projects.list(all=True, membership=True)
for project in projects:
    print(project)


# alice = gl.users.list(username='chaoneng')[0]
# print(alice)

# project = gl.projects.get(673)
# print(project)
#
# project.members.delete(12)
