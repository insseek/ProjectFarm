# Generated by Django 2.0 on 2020-05-07 16:25

from django.db import migrations, models


def data_migrate_lead_requirement_to_client_info_proposal(apps, schema_editor):
    Proposal = apps.get_model("proposals", "Proposal")
    RequirementInfo = apps.get_model("clients", "RequirementInfo")
    ClientInfo = apps.get_model("clients", "ClientInfo")

    # from clients.models import RequirementInfo, ClientInfo, Lead
    # from proposals.models import Proposal
    ClientInfo.objects.filter(lead__proposal__isnull=True).delete()

    requirements = RequirementInfo.objects.all()
    for requirement in requirements:
        lead = requirement.lead
        proposal = getattr(lead, 'proposal', None)
        client_info = ClientInfo.objects.filter(lead_id=lead.id).first()
        if not proposal:
            if client_info:
                client_info.delete()
            continue

        if client_info:
            client_info.proposal = proposal
            client_info.save()
            continue

        ClientInfo.objects.create(
            proposal=proposal,
            lead=lead,
            company=lead.company,
            company_name=lead.company_name,
            address=lead.address,
            contact_name=lead.contact_name,
            contact_job=lead.contact_job,
            phone_number=lead.phone_number,
            client_background=requirement.client_background,
            client_background_remarks=requirement.client_background_remarks,
            contact_role=requirement.contact_role,
            decision_making_capacity=requirement.appeal_background_one,
            technical_capacity=requirement.appeal_background_two,
            communication_cost=requirement.communication_cost,
            rebate=requirement.appeal_background_three,
            rebate_proportion=requirement.rebate_proportion,
            submitter=requirement.submitter,
            created_at=requirement.created_at,
            modified_at=requirement.modified_at,
        )
        proposal.business_objective = requirement.business_objective
        proposal.period = requirement.period
        if requirement.available_material:
            available_material = set()
            for i in requirement.available_material:
                if i == '0':
                    continue
                elif i == '6':
                    available_material.add('5')
                elif i == '7':
                    available_material.add('9')
                else:
                    available_material.add(i)
            proposal.available_material = list(available_material)
            proposal.material_remarks = requirement.material_remarks
        if requirement.reference != '3':
            proposal.reference = requirement.reference
            proposal.reference_remarks = requirement.reference_remarks
        if requirement.rigid_requirement:
            rigid_requirements = set()
            for i in requirement.rigid_requirement:
                if i == '0':
                    continue
                elif i == '2':
                    available_material.add('9')
                else:
                    available_material.add(i)
            proposal.rigid_requirement = list(rigid_requirements)
            proposal.rigid_requirement_remarks = requirement.rigid_requirement_remarks
        proposal.save()

    proposals = Proposal.objects.all()
    for proposal in proposals:
        if proposal.remarks:
            proposal.description = proposal.description + '\n' + proposal.remarks
            proposal.remarks = None
            proposal.save()


class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0058_proposal_decision_email'),
        ('clients', '0049_clientinfo_proposal'),
    ]

    operations = [
        migrations.RunPython(data_migrate_lead_requirement_to_client_info_proposal, migrations.RunPython.noop),
    ]
