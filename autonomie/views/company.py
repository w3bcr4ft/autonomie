# -*- coding: utf-8 -*-
# * File Name : company.py
#
# * Copyright (C) 2010 Gaston TJEBBES <g.t@majerti.fr>
# * Company : Majerti ( http://www.majerti.fr )
#
#   This software is distributed under GPLV3
#   License: http://www.gnu.org/licenses/gpl-3.0.txt
#
# * Creation Date : 27-03-2012
# * Last Modified :
#
# * Project : autonomie
#
"""
    Views for the company handling
    Entry point for the main users
"""
import logging
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound
from pyramid.security import has_permission

from autonomie.models.company import Company
from autonomie.utils.forms import merge_session_with_post
from autonomie.views.forms.utils import BaseFormView
from autonomie.views.forms.company import CompanySchema
from autonomie.utils.widgets import ViewLink
from autonomie.utils.views import submit_btn

log = logging.getLogger(__name__)

def company_index(request):
    """
        index page for the company shows latest news :
            - last validated estimation/invoice
            - To be relaunched bill
    """
    company = request.context
    ret_val = dict(title=company.name.title(),
                company=company)
    # recovering last activities
    all_tasks = []
    all_invoices = []
    for project in company.projects:
        all_tasks.extend(project.estimations)
        all_tasks.extend(project.invoices)
        all_invoices.extend(project.invoices)

    all_tasks = sorted(all_tasks,
                        key=lambda a: a.statusDate,
                        reverse=True)
    ret_val['tasks'] = all_tasks[:5]

    # recovering elapsed invoices for warning
    elapsed_invoices = [invoice
                        for invoice in all_invoices if invoice.is_tolate()]
    elapsed_invoices = sorted(elapsed_invoices,
                              key=lambda a: a.taskDate,
                              reverse=True)
    ret_val['elapsed_invoices'] = elapsed_invoices
    return ret_val

def company_view(request):
    """
        Company main view
    """
    company = request.context
    populate_actionmenu(request, request.context)
    link_list = []
    link_list.append(ViewLink(u"Voir les clients",
            "manage", path="company_clients", id=company.id,
            icon='icon-arrow-right'
            ))
    link_list.append(ViewLink(u"Voir les projets",
            "manage", path="company_projects", id=company.id,
            icon='icon-arrow-right'
            ))
    link_list.append(ViewLink(u"Voir les factures",
            "manage", path="company_invoices", id=company.id,
            icon='icon-arrow-right'
            ))
    return dict(title=company.name.title(),
                company=company,
                link_list=link_list)

class CompanyAdd(BaseFormView):
    """
        View class for company add
    """
    add_template_vars = ('title',)
    title = u"Ajouter une entreprise"
    schema = CompanySchema()
    buttons = (submit_btn,)

    def before(self, form):
        """
            prepopulate the form and the actionmenu
        """
        populate_actionmenu(self.request)

    def submit_success(self, appstruct):
        """
            Edit the database entry and return reidrect
        """
        company = Company()
        company = merge_session_with_post(company, appstruct)
        self.dbsession.add(company)
        self.dbsession.flush()
        message = u"L'entreprise '{0}' a bien été ajoutée".format(company.name)
        self.session.flash(message)
        return HTTPFound(self.request.route_path("company", id=company.id))



class CompanyEdit(BaseFormView):
    """
        View class for company editing
    """
    add_template_vars = ('title',)
    schema = CompanySchema()
    buttons = (submit_btn,)

    @reify
    def title(self):
        """
            title property
        """
        return u"Édition de {0}".format(self.request.context.name.title())

    def before(self, form):
        """
            prepopulate the form and the actionmenu
        """
        form.appstruct = self.request.context.appstruct()
        populate_actionmenu(self.request, self.request.context)

    def submit_success(self, appstruct):
        """
            Edit the database entry and return reidrect
        """
        company = merge_session_with_post(self.request.context, appstruct)
        company = self.dbsession.merge(company)
        self.dbsession.flush()
        message = u"Votre entreprise a bien été éditée"
        self.session.flash(message)
        return HTTPFound(self.request.route_path("company", id=company.id))

def populate_actionmenu(request, company=None):
    """
        add item in the action menu
    """
    request.actionmenu.add(get_list_view_btn())
    if company is not None:
        request.actionmenu.add(get_view_btn(company.id))
        if has_permission('edit', request.context, request):
            request.actionmenu.add(get_edit_btn(company.id))

def get_list_view_btn():
    """
        Return a link to the CAE's directory
    """
    return ViewLink(u"Annuaire", "view", path="users")

def get_view_btn(company_id):
    """
        Return a link to the view page
    """
    return ViewLink(u"Voir", "view", path="company", id=company_id)

def get_edit_btn(company_id):
    """
        Return a link to the edition form
    """
    return ViewLink(u"Éditer", "edit", path="company", id=company_id,
                                            _query=dict(action="edit"))

def includeme(config):
    """
        Add all company related views
    """
    config.add_route('company', '/company/{id:\d+}', traverse='/companies/{id}')
    config.add_view(company_index,
                    route_name='company',
                    renderer='company_index.mako',
                    request_param='action=index',
                    permission='edit')
    config.add_view(company_view,
                    route_name='company',
                    renderer='company.mako',
                    permission="view")
    config.add_view(CompanyEdit,
                    route_name='company',
                    renderer='company_edit.mako',
                    request_param='action=edit',
                    permission="edit")
#    config.add_view(CompanyAdd,
