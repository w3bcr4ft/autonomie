# -*- coding: utf-8 -*-
# * Copyright (C) 2012-2013 Croissance Commune
# * Authors:
#       * Arezki Feth <f.a@majerti.fr>;
#       * Miotte Julien <j.m@majerti.fr>;
#       * Pettier Gabriel;
#       * TJEBBES Gaston <g.t@majerti.fr>
#
# This file is part of Autonomie : Progiciel de gestion de CAE.
#
#    Autonomie is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Autonomie is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Autonomie.  If not, see <http://www.gnu.org/licenses/>.
#

"""
    User related views
"""
import logging
import colander
import peppercorn
import deform
from traceback import print_exc

from colanderalchemy import SQLAlchemySchemaNode
from js.deform import auto_need
from webhelpers.html.builder import HTML
from sqlalchemy import (
    or_,
    distinct,
)
from pyramid.httpexceptions import HTTPFound
from pyramid.security import has_permission
from pyramid.decorator import reify

from autonomie.models import files
from autonomie.models.base import DBSESSION
from autonomie.models.user import (
    User,
    UserDatas,
    UserDatasSocialDocTypes,
    SocialDocTypeOption,
    CompanyDatas,
    USERDATAS_FORM_GRIDS,
)
from autonomie.models.files import (
    File,
    TemplatingHistory,
)
from autonomie.models.company import (
    Company,
    CompanyActivity,
)
from autonomie.utils.widgets import (
    ViewLink,
    PopUp,
    StaticWidget,
)
from autonomie.export.utils import write_file_to_request
from sqla_inspect import py3o
from deform_extensions import (
    AccordionFormWidget,
    TableFormWidget,
)
from autonomie.forms.user import (
    get_list_schema,
    get_account_schema,
    get_password_schema,
    get_user_schema,
    get_userdatas_schema,
    get_userdatas_list_schema,
    UserDisableSchema,
    get_company_association_schema,
)
from autonomie.views import (
    BaseListView,
    BaseXlsView,
    submit_btn,
    cancel_btn,
    BaseFormView,
)
from autonomie.views.render_api import format_account
from autonomie.views.company import company_enable
from autonomie.views.files import (
    get_add_file_link,
    FileUploadView,
)

log = logging.getLogger(__name__)


DOCTYPE_VALIDATION_BTN = deform.Button(
    name='submit',
    type='submit',
    title=u'Enregistrer les statuts de documents',
)


def get_user_form(request):
    """
        Return the user add form
    """
    schema = get_user_schema().bind(request=request)
    return deform.Form(schema, buttons=(submit_btn,))


def get_doctypes_form_schema(userdatas_model):
    """
    Returns a dynamically built form for doctypes registration
    """
    registrations = userdatas_model.doctypes_registrations
    node_schema = SQLAlchemySchemaNode(UserDatasSocialDocTypes)

    appstruct = {}
    form_schema = colander.Schema()

    for index, registration in enumerate(registrations):
        node = node_schema.clone()
        name = 'node_%s' % index
        node.name = name
        node.title = u''
        node['status'].title = registration.doctype.label
        form_schema.add(node)
        appstruct[name] = node_schema.dictify(registration)

    return form_schema, appstruct


class PermanentUserAddView(BaseFormView):
    """
    User add form, allows to add :

        * managers
        * admins
    """
    title = u"Ajout d'un nouveau compte"
    validate_msg = u"Le compte a bien été ajouté"
    schema = get_user_schema()

    def _get_company(self, name, user):
        """
            Return a company object, create a new one if needed
        """
        query = Company.query()
        company = query.filter(Company.name==name).first()
        #avoid creating duplicate companies
        if company is None:
            company = self._add_company(name, user)
        return company

    def _add_company(self, name, user):
        """
            Add a company 'name' in the database
            ( set its goal by default )
        """
        log.info(u"Adding company : %s" % name)
        company = Company()
        company.name = name
        company.goal = u"Entreprise de {0}".format(
            format_account(user, reverse=False)
        )
        company.contribution = self.request.config.get('contribution_cae')
        company = self.dbsession.merge(company)
        self.dbsession.flush()
        return company

    def before(self, form):
        """
            populate the actionmenu before entering the view
        """
        populate_actionmenu(self.request)

    def redirect_url(self, user_model):
        """
        Return the url we should redirect to
        """
        return self.request.route_path("user", id=user_model.id)

    def _handle_companies(self, company_names, user_model):
        """
        Handle companies if needed

        if company_names is None (contractor case): nothing happens
        if company_names is [] (permanent case): user will have no companies
        """
        if company_names is not None:
            companies = []

            for company_name in company_names:
                company = self._get_company(company_name, user_model)
                companies.append(company)
            user_model.companies = companies

    def submit_success(self, appstruct):
        """
            Add a user to the database
            Add its companies
            Add a relationship between companies and the new account
        """
        if "companies" in appstruct:
            company_names = set(appstruct.pop('companies'))
        else:
            company_names = None

        groups = set(appstruct.pop('groups', []))
        password = appstruct.pop('pwd', None)

        if self.context.__name__ == 'user':
            user_model = self.schema.objectify(appstruct, self.context)
            log.info(u"Edit user : {0}" .format(format_account(user_model)))
        else:
            user_model = self.schema.objectify(appstruct)
            log.info(u"Add user : {0}" .format(format_account(user_model)))

        if password is not None:
            user_model.set_password(password)

        user_model.groups = groups

        self._handle_companies(company_names, user_model)

        user_model = self.dbsession.merge(user_model)

        # Here we flush to get an id for the redirect
        self.dbsession.flush()

        self.session.flash(self.validate_msg)
        return HTTPFound(self.redirect_url(user_model))


class PermanentUserEditView(PermanentUserAddView):
    """
        User edition view
    """
    validate_msg = u"Le compte a bien été modifié"
    schema = get_user_schema(edit=True)

    @reify
    def title(self):
        """
            form title
        """
        return u"Modification de {0}".format(
            format_account(self.context)
        )

    def before(self, form):
        """
            Set the context datas in the view attributes before view execution
        """
        appstruct = self.schema.dictify(self.context)
        appstruct.pop('pwd')

        appstruct['companies'] = [c.name for c in self.context.companies]
        form.set_appstruct(appstruct)
        populate_actionmenu(self.request, self.context)


class UserEditView(PermanentUserEditView):
    """
    Contractor's account edition view
    """
    schema = get_user_schema(edit=True, permanent=False)

    def redirect_url(self, user_model):
        """
        Redirect to the userdatas view associated to the given model
        pass also the form3 tab name
        """
        return self.request.route_path(
            "userdata",
            id=user_model.userdatas.id,
            _anchor='tab3'
        )


class UserList(BaseListView):
    """
        List the users
        Allows to search for companies or user name
        Sorting is allowed on names and emails
    """
    title = u"Annuaire des utilisateurs"
    # The schema used to validate our search/filter form
    schema = get_list_schema()
    # The columns that allow sorting
    sort_columns = dict(name=User.lastname,
                        email=User.email)

    def query(self):
        """
            Return the main query for our list view
        """
        log.debug("Queryiing")
        query = DBSESSION().query(distinct(User.id), User)
        return query.outerjoin(User.companies)

    def filter_name_search(self, query, appstruct):
        """
            filter the query with the provided search argument
        """
        log.debug("Filtering name")
        search = appstruct['search']
        if search:
            query = query.filter(
            or_(User.lastname.like("%" + search + "%"),
                User.firstname.like("%" + search + "%"),
                User.companies.any(Company.name.like("%" + search + "%")),
                User.companies.any(Company.goal.like("%" + search + "%"))
                ))

        return query

    def filter_activity_id(self, query, appstruct):
        """
        filter the query with company activities
        """
        log.debug("Filtering by activity id")
        log.debug(appstruct)
        activity_id = appstruct.get('activity_id')
        if activity_id:
            query = query.filter(
                User.companies.any(
                    Company.activities.any(
                        CompanyActivity.id == activity_id
                    )
                )
            )
            log.debug(query)
        return query

    def filter_disabled(self, query, appstruct):
        disabled = appstruct['disabled']
        if disabled == '0':
            val = 'Y'
        else:
            val = 'N'
        return query.filter(User.active == val)

    def populate_actionmenu(self, appstruct):
        """
            Add items to the action menu (directory link,
            add user link and popup for user with add permission ...)
        """
        populate_actionmenu(self.request)

        if has_permission("add", self.context, self.request):
            form = get_user_form(self.request)
            popup = PopUp("add", u'Ajouter un permanent', form.render())
            self.request.popups = {popup.name: popup}
            self.request.actionmenu.add(popup.open_btn())

        self.request.actionmenu.add(get_add_contractor_btn())

        if has_permission("manage", self.context, self.request):
            self.request.actionmenu.add(self._get_disabled_btn(appstruct))

        self.request.actionmenu.add(get_userdatas_link_btn())

    def _get_disabled_btn(self, appstruct):
        """
            return the button to show disabled users
        """
        disabled = appstruct['disabled']
        if disabled == '0':
            url = self.request.current_route_path(_query=dict(disabled="1"))
            link = HTML.a(u"Afficher les comptes désactivés",  href=url)
        else:
            url = self.request.current_route_path(_query=dict(disabled="0"))
            link = HTML.a(u"Afficher uniquement les comptes actifs", href=url)
        return StaticWidget(link)


class UserAccountView(BaseFormView):
    """
        User account view with password edition
    """
    schema = get_password_schema()
    title = u"Mon compte"

    def before(self, form):
        """
            Called before view execution
        """
        appstruct = {'login': self.request.user.login}
        form.set_appstruct(appstruct)

    def submit_success(self, appstruct):
        """
            Called on submission success -> changing password
        """
        log.info(u"# User {0} has changed his password #".format(
                        self.request.user.login))
        new_pass = appstruct['pwd']
        self.request.user.set_password(new_pass)
        self.dbsession.merge(self.request.user)
        self.request.session.flash(u"Votre mot de passe a bien été modifié")
        return HTTPFound(self.request.route_path('account'))


class UserAccountEditView(BaseFormView):
    """
    View allowing a end user to modify some of his account informations
    """
    schema = get_account_schema()
    msg = u"Vos modifications ont bien été enregistrées"

    def before(self, form):
        form.set_appstruct(self.schema.dictify(self.context))

    def submit_success(self, appstruct):
        model = self.schema.objectify(appstruct, self.context)
        self.dbsession.merge(model)
        self.request.session.flash(self.msg)
        return HTTPFound(
            self.request.route_path('account')
        )


class UserDatasAdd(BaseFormView):
    title = u"Gestion sociale"
    schema = get_userdatas_schema() #SQLAlchemySchemaNode(UserDatas)
    validation_msg = u"Les informations sociales ont bien été enregistrées"
    form_options = (('formid', "userdatas_edit"),)
    buttons = (submit_btn, cancel_btn,)

    def before(self, form):
        auto_need(form)
        form.widget = AccordionFormWidget(grids=USERDATAS_FORM_GRIDS)
        self.populate_actionmenu()

    def populate_actionmenu(self):
        self.request.actionmenu.add(get_userdatas_list_btn())

    def submit_success(self, appstruct):
        if self.context.__name__ == 'userdatas':
            model = self.schema.objectify(appstruct, self.context)
        else:
            from autonomie.views import render_api
            confirmation = self.request.GET.get('confirmation', '0')
            lastname = appstruct['coordonnees_lastname']
            email = appstruct['coordonnees_email1']
            if lastname and confirmation == '0':
                query = UserDatas.query().filter(
                    or_(
                        UserDatas.coordonnees_lastname==lastname,
                        UserDatas.coordonnees_email1==email,
                    )
                )
                query_count = query.count()
                if query_count > 0:
                    if query_count == 1:
                        msg = u"Une entrée de gestion sociale similaire \
a déjà été créée: <ul>"
                    else:
                        msg = u"{0} entrées de gestion sociale similaires ont \
déjà été créées : <ul>".format(query_count)

                    for entry in query:
                        msg += u"<li><a href='%s'>%s (%s)</a></li>" % (
                            self.request.route_path('userdata', id=entry.id),
                            render_api.format_account(entry),
                            entry.coordonnees_email1,
                        )
                    msg += u"</ul>"
                    form = self._get_form()
                    form.action = self.request.current_route_path(
                        _query={'action': 'new', 'confirmation':'1'}
                    )
                    form.set_appstruct(appstruct)
                    datas = dict(
                        form=form.render(),
                        confirmation_message=msg,
                        confirm_form_id=form.formid,
                    )
                    datas.update(self._more_template_vars())
                    return datas


            model = self.schema.objectify(appstruct)

        model = self.dbsession.merge(model)
        self.dbsession.flush()

        user, login, password = model.gen_user_account()

        companies = model.gen_companies()
        if companies:
            msg = u"Les activités associées ont été ajoutées"
            self.request.session.flash(msg)
            user.companies = companies

        model = self.dbsession.merge(model)
        self.dbsession.flush()

        if user is not None:
            url = self.request.route_path('user', id=user.id)

            msg = u"Un compte a été créé : \
login : {0}, \
mot de passe : {1}".format(login, password, url)

            self.request.session.flash(msg)

        self.session.flash(self.validation_msg)
        return HTTPFound(self.request.route_path('userdata', id=model.id))

    def cancel_success(self, appstruct):
        return HTTPFound(self.request.route_path('userdatas'))

    cancel_failure = cancel_success


class UserDatasEdit(UserDatasAdd):
    add_template_vars = (
        'doctypes_form',
        'account_form',
        'doctemplates',
    )

    @property
    def title(self):
        return u"Gestion sociale : {0}".format(
            format_account(self.request.context)
        )

    def before(self, form):
        super(UserDatasEdit, self).before(form)
        form.set_appstruct(self.schema.dictify(self.request.context))
        self.counter = form.counter
        self.ensure_doctypes_rel()

    def populate_actionmenu(self):
        self.request.actionmenu.add(get_userdatas_list_btn())
        self.request.actionmenu.add(get_add_file_link(self.request))

    def ensure_doctypes_rel(self):
        """
        Ensure the current userdata context is related to all doctypes through a
        UserDatasSocialDocTypes object
        """
        userdatas_id = self.context.id

        for doctype in SocialDocTypeOption.query():
            doctype_id = doctype.id
            rel = UserDatasSocialDocTypes.get((userdatas_id, doctype_id,))
            if rel is None:
                rel = UserDatasSocialDocTypes(
                    userdatas_id=userdatas_id,
                    doctype_id=doctype_id,
                )
                self.dbsession.add(rel)

    @property
    def account_form(self):
        """
        Return a user account edition form
        """
        form = None
        if self.context.user_id is not None:
            # There is an associated user account
            schema = get_user_schema(edit=True, permanent=False)
            schema = schema.bind(request=self.request)
            action = self.request.route_path(
                'user',
                id=self.context.user_id,
                _query=dict(action="edit"),
            )
            form = deform.Form(
                schema,
                buttons = (submit_btn,),
                action=action,
                counter=self.counter,
            )

            user_obj = self.context.user

            appstruct = schema.dictify(user_obj)
            appstruct.pop('pwd')
            appstruct['companies'] = [c.name for c in user_obj.companies]
            appstruct['groups'] = user_obj.groups
            form.set_appstruct(appstruct)
        return form

    @property
    def doctypes_form(self):
        """
        Add a doctype registration form to the resulting dict
        """
        form_schema, appstruct = get_doctypes_form_schema(self.context)
        action = self.request.route_path(
            'userdata',
            id=self.context.id,
            _query=dict(action="doctype"),
        )
        form = deform.Form(
            form_schema,
            buttons=(submit_btn,),
            action=action,
            counter=self.counter
        )
        form.widget = TableFormWidget()
        form.set_appstruct(appstruct)
        return form

    @property
    def doctemplates(self):
        templates = files.Template.query()
        templates = templates.filter(files.Template.active==True)
        return templates.all()


class CompanyAssociationView(BaseFormView):
    """
    Associate a user with a company
    """
    title = u"Associer un utlisateur à une entreprise"
    schema = get_company_association_schema()

    def before(self, form):
        self.request.actionmenu.add(
            ViewLink(
                "Retour",
                "manage",
                path="userdata",
                id=self.context.id,
                _anchor="tab5"
            )
        )

    def submit_success(self, appstruct):
        for name in appstruct.get('companies', []):
            company = Company.query().filter(Company.name==name).first()
            if company is not None:
                self.context.user.companies.append(company)
                self.request.dbsession.merge(self.context.user)

        url = self.request.route_path(
            "userdata",
            id=self.context.id,
            _anchor="tab5"
        )
        return HTTPFound(url)



def record_compilation(context, request, template):
    """
    Record the compilation of a template to be able to build an history
    """
    if isinstance(context, UserDatas):
        history = files.TemplatingHistory(
            user_id=request.user.id,
            userdatas_id=context.id,
            template_id=template.id)
        log.debug(u"Storing an history object")
        request.dbsession.add(history)


def delete_templating_history_view(context, request):
    userdatas = context.userdatas
    request.dbsession.delete(context)
    request.session.flash(u"L'élément a bien été supprimé de l'historique")
    return HTTPFound(
        request.route_path(
            'userdata',
            id=userdatas.id,
            _anchor='tab4'
        )
    )

def py3o_view(context, request):
    """
    py3o view :

        compile the template provided as argument using the current view
        context for templating
    """
    log.debug(u"Asking for a template compilation")
    doctemplate_id = request.GET.get('template_id')

    if doctemplate_id:
        template = files.Template.get(doctemplate_id)
        if template:
            log.debug(" + Templating (%s, %s)" % (template.name, template.id))
            try:
                output = py3o.compile_template(
                    context,
                    template.data_obj,
                    request.config
                )
                write_file_to_request(
                    request,
                    template.name,
                    output,
                )
                record_compilation(context, request, template)
                return request.response
            except Exception, err:
                print_exc()
                log.exception(
u"Une erreur est survenue à la compilation du template %s avec un contexte \
de type %s et d'id %s" % (template.id, context.__class__, context.id)
                             )
                request.session.flash(
                    u"Erreur à la compilation du modèle, merci de contacter \
votre administrateur",
                    "error"
                )
        else:
            request.session.flash(
                u"Impossible de mettre la main sur ce modèle",
                "error"
            )
    else:
        request.session.flash(
            u"Les données fournies en paramètres sont invalides",
            "error"
        )
    return HTTPFound(request.route_path(context.type_, id=context.id))


def userdata_doctype_view(userdata_model, request):
    """
    View used to register doctypes status

        userdata_model

            The UserDatas model retrieved through traversal
    """
    if 'submit' in request.params:
        schema = get_doctypes_form_schema(userdata_model)[0]
        appstruct = request.POST.items()
        appstruct = peppercorn.parse(appstruct)
        try:
            appstruct = schema.deserialize(appstruct)
        except colander.Invalid, exc:
            log.exception(
                "Error while validating doctype registration"
            )
        else:
            node_schema = SQLAlchemySchemaNode(UserDatasSocialDocTypes)
            for data in appstruct.values():
                model = node_schema.objectify(data)
                request.dbsession.merge(model)
            request.session.flash(
                u"Les informations saisies ont bien été enregistrées"
            )

    return HTTPFound(
        request.route_path('userdata', id=userdata_model.id)
    )


class UserDatasListClass(object):
    """
    User datas list view
    """
    title = u"Liste des informations sociales"
    schema = get_userdatas_list_schema()
    sort_columns = dict(
        lastname=UserDatas.coordonnees_lastname,
    )
    default_sort = 'lastname'

    def query(self):
        return UserDatas.query()

    def filter_situation_situation(self, query, appstruct):
        """
        Filter the general situation of the project
        """
        log.debug("APPSTRUCT : %s" % appstruct)
        situation = appstruct.get('situation_situation')
        if situation is not None:
            query = query.filter(
                UserDatas.situation_situation_id==situation
            )
        return query

    def filter_search(self, query, appstruct):
        """
        Filter the current query for firstname, lastname or activity
        """
        search = appstruct.get('search')

        if search not in (None, ''):
            filter_ = "%" + search + "%"
            query = query.filter(
                or_(
                    UserDatas.coordonnees_firstname.like(filter_),
                    UserDatas.coordonnees_lastname.like(filter_),
                    UserDatas.activity_companydatas.any(
                        CompanyDatas.name.like(filter_)),
                    UserDatas.activity_companydatas.any(
                        CompanyDatas.title.like(filter_)),
                )
            )
        return query

    def filter_situation_follower_id(self, query, appstruct):
        """
        Filter the current query through followers
        """
        follower_id = appstruct.get('situation_follower_id')

        if follower_id not in (None, -1):
            query = query.filter(
                UserDatas.situation_follower_id==follower_id
            )
        return query


class UserDatasListView(UserDatasListClass, BaseListView):
    """
    The userdatas listing view
    """
    pass


class UserDatasXlsView(UserDatasListClass, BaseXlsView):
    """
        Userdatas excel view
    """
    model = UserDatas

    @property
    def filename(self):
        return "gestion_social.xls"


def user_view(request):
    """
        Return user view only datas
    """
    title = u"{0}".format(format_account(request.context))
    populate_actionmenu(request, request.context)
    return dict(title=title,
                user=request.context)


def user_delete(account, request):
    """
        disable a user and its enteprises
    """
    try:
        # First we disable associated companies if we're going to delete the
        # only employee
        for company in account.companies:
            if len(company.employees) == 1:
                company.disable()
                request.dbsession.merge(company)

        log.debug(u"Deleting account : {0}".format(format_account(account)))
        request.dbsession.delete(account)
        request.dbsession.flush()
        message = u"Le compte '{0}' a bien été supprimé".format(
                                        format_account(account))
        request.session.flash(message)
    except:
        log.exception(u"Erreur à la suppression du compte")
        err_msg = u"Erreur à la suppression du compte de '{0}'".format(
                                            format_account(account))
        request.session.flash(err_msg, 'error')
    return HTTPFound(request.route_path("users"))


def userdatas_delete(userdatas, request):
    """
    delete a user account and its userdatas
    """
    if userdatas.user is not None:
        log.debug(u"Suppression des données  et du compte de : {0}".format(
            format_account(userdatas)
        ))
        # Suppression du compte utilisateur (la cascade va entrainer la
        # suppression des données associées)
        user_delete(userdatas.user, request)
        message = u"Les données de '{0}' ont bien été effacées".format(
                                        format_account(userdatas))
        request.session.flash(message)
    else:
        try:
            log.debug(u"Suppression des données de : {0}".format(
                format_account(userdatas)
            ))
            request.dbsession.delete(userdatas)
            request.dbsession.flush()
            message = u"Les données de '{0}' ont bien été effacées".format(
                                            format_account(userdatas))
            request.session.flash(message)
        except:
            log.exception(u"Erreur à la suppression des données")
            err_msg = u"Erreur à la suppression des données de '{0}'".format(
                                                format_account(userdatas))
            request.session.flash(err_msg, 'error')
    return HTTPFound(request.route_path('userdatas'))


def user_enable(request):
    """
        enable a user and its enterprise (if he has only one)
    """
    account = request.context
    if not account.enabled():
        try:
            account.enable()
            request.dbsession.merge(account)
            log.info(u"The user {0} has been enabled".\
                    format(format_account(account)))
            message = u"L'utilisateur {0} a été (ré)activé.".\
                    format(format_account(account))
            request.session.flash(message)
            if len(account.companies) == 1:
                company = account.companies[0]
                company_enable(request, company=company)
        except:
            log.exception(u"Erreur à l'activation du compte")
            err_msg = u"Erreur à l'activation du compte de '{0}'".\
                    format(format_account(account))
            request.session.flash(err_msg, 'error')
    return HTTPFound(request.route_path("users"))


class UserDisable(BaseFormView):
    """
        Allows to disable user's and optionnaly its companies
    """
    schema = UserDisableSchema()
    buttons = (submit_btn, cancel_btn,)

    @reify
    def title(self):
        """
            title of the form
        """
        return u"Désactivation du compte {0}".format(
            format_account(self.context)
        )

    def before(self, form):
        """
            Redirect if the cancel button was clicked
        """
        if "cancel" in self.request.POST:
            user_id = self.context.id
            raise HTTPFound(self.request.route_path("user", id=user_id))

    def _get_redirect_url(self):
        """
        Return the url we want to redirect the user to
        """
        if getattr(self.context, 'userdatas', None):
            return self.request.route_path(
                "userdata",
                id=self.context.userdatas.id
            )
        else:
            return self.request.route_path("user", id=self.context.id)

    def submit_success(self, appstruct):
        """
            Disable users and companies
        """
        if appstruct.get('companies', False):
            self._disable_companies()
        if appstruct.get('disable', False):
            self._disable_user(self.context)
        return HTTPFound(self._get_redirect_url())

    def _disable_user(self, user):
        """
            disable the current user
        """
        if user.enabled():
            user.disable()
            self.dbsession.merge(user)
            log.info(u"The user {0} has been disabled".format(
                         format_account(user))
            )
            message = u"L'utilisateur {0} a été désactivé.".format(
                format_account(user)
            )
            self.session.flash(message)

    def _disable_companies(self):
        """
            disable all companies related to the current user
        """
        for company in self.request.context.companies:
            company.disable()
            self.dbsession.merge(company)
            log.info(
                u"The company {0} has been disabled".format(company.name)
            )
            message = u"L'entreprise '{0}' a bien été désactivée.".format(
                company.name
            )
            self.session.flash(message)
            for employee in company.employees:
                self._disable_user(employee)


def populate_actionmenu(request, user=None):
    """
        populate the actionmenu
    """
    request.actionmenu.add(get_list_view_btn())
    if user:
        request.actionmenu.add(get_view_btn(user.id))
        if has_permission('edit', request.context, request):
            request.actionmenu.add(get_edit_btn(user))
            if user.enabled():
                request.actionmenu.add(get_disable_btn(user.id))
            else:
                request.actionmenu.add(get_enable_btn(user.id))
                request.actionmenu.add(get_del_btn(user.id))


def get_list_view_btn():
    """
        Return a link to the user list
    """
    return ViewLink(u"Annuaire", "view", path="users")


def get_userdatas_list_btn():
    """
    Return a link to the user datas list
    """
    return ViewLink(u"Annuaire 'Gestion sociale'", "manage", path="userdatas")


def get_view_btn(user_id):
    """
        Return a link for user view
    """
    return ViewLink(u"Voir", "view", path="user", id=user_id)


def get_edit_btn(user):
    """
        Return a link for user edition
    """
    if user.is_contractor():
        return ViewLink(
            u"Modifier",
            "manage",
            path="userdata",
            id=user.userdatas.id,
            _anchor='form3',
        )
    else:
        return ViewLink(
            u"Modifier",
            "manage",
            path="user",
            id=user.id,
            _query=dict(action="edit_permanent"),
        )


def get_enable_btn(user_id):
    return ViewLink(u"Activer", "manage", path="user", id=user_id,
                                        _query=dict(action="enable"))


def get_disable_btn(user_id):
    """
        Return the button used to disable an account
    """
    return ViewLink(u"Désactiver", "manage", path="user", id=user_id,
                                        _query=dict(action="disable"))


def get_add_contractor_btn():
    """
    Return a button returning the end user to the userdatas page to add a new
    account
    """
    return ViewLink(
        u"Ajouter un entrepreneur",
        "add",
        path="userdatas",
        _query=dict(action='new'),
    )


def get_userdatas_link_btn():
    """
    Return a button leading to the userdatas list view
    """
    return ViewLink(
        u"Annuaire gestion sociale",
        "manage",
        path="userdatas",
    )


def get_del_btn(user_id):
    """
        Return the button used to delete an account
    """
    message = u"Êtes-vous sûr de vouloir supprimer ce compte ? \
Cette action n'est pas réversible."
    return ViewLink(u"Supprimer", "manage", confirm=message, path="user",
                                     id=user_id, _query=dict(action="delete"))


def mydocuments_view(context, request):
    """
    View callable collecting datas for showing the social docs associated to the
    current user's account
    """
    if request.user.userdatas is not None:
        query = File.query()
        documents = query.filter(
            File.parent_id==request.user.userdatas.id
        ).all()
        query = TemplatingHistory.query()
        generated_docs = query.filter(
            TemplatingHistory.userdatas_id==request.user.userdatas.id,
        ).all()
    else:
        documents = []
    return dict(
        title=u"Mes documents",
        documents=documents,
        generated_docs=generated_docs,
    )


def includeme(config):
    """
        Declare all the routes and views related to this model
    """
    config.add_route("users", "/users")

    config.add_route(
        "user",
        "/users/{id:\d+}",
        traverse="/users/{id}",
    )

    config.add_route(
        "userdata",
        "/userdatas/{id:\d+}",
        traverse="/userdatas/{id}",
    )

    config.add_route(
        "userdatas",
        "/userdatas",
    )

    config.add_route(
        "userdatas.xls",
        "/userdatas.xls",
    )
    config.add_route(
        "templatinghistory",
        "/py3ostory/{id}",
        traverse="/templatinghistory/{id}"
    )

    config.add_view(
        delete_templating_history_view,
        route_name="templatinghistory",
        request_param="action=delete",
        permission="manage",
    )

    config.add_route('account', '/account')

    config.add_view(
        UserList,
        route_name='users',
        renderer='users.mako',
        permission='view'
    )

    config.add_view(
        user_view,
        route_name='user',
        renderer='user.mako',
        permission='view',
    )

    config.add_view(
        PermanentUserAddView,
        route_name='users',
        renderer='base/formpage.mako',
        request_method='POST',
        permission='add',
    )

    config.add_view(
        PermanentUserEditView,
        route_name='user',
        renderer='base/formpage.mako',
        request_param='action=edit_permanent',
        permission='manage',
    )

    config.add_view(
        UserEditView,
        route_name='user',
        renderer='base/formpage.mako',
        request_param='action=edit',
        permission='manage',
    )

    config.add_view(
        UserAccountEditView,
        route_name='user',
        renderer='base/formpage.mako',
        request_param='action=accountedit',
        permission='edit',
    )

    config.add_view(
        UserDatasAdd,
        route_name='userdatas',
        request_param='action=new',
        renderer='/userdata.mako',
        permission='manage',
    )

    config.add_view(
        UserDatasEdit,
        route_name='userdata',
        renderer='/userdata.mako',
        permission='manage'
    )

    config.add_view(
        userdata_doctype_view,
        route_name='userdata',
        request_param='action=doctype',
        permission='manage',
    )

    config.add_view(
        UserDisable,
        route_name='user',
        renderer='base/formpage.mako',
        request_param='action=disable',
        permission='edit',
    )

    config.add_view(
        user_enable,
        route_name='user',
        renderer='base/formpage.mako',
        request_param='action=enable',
        permission='edit'
    )

    config.add_view(
        user_delete,
        route_name='user',
        request_param='action=delete',
        permission='manage'
    )

    config.add_view(
        userdatas_delete,
        route_name='userdata',
        request_param='action=delete',
        permission='manage'
    )

    config.add_view(
        CompanyAssociationView,
        route_name='userdata',
        request_param='action=associate',
        renderer="base/formpage.mako",
        permission='manage'
    )

    config.add_view(
        UserAccountView,
        route_name='account',
        renderer='account.mako',
        permission='view'
    )

    config.add_view(
        UserDatasListView,
        route_name="userdatas",
        renderer="userdatas.mako",
        permission="manage",
    )

    config.add_view(
        UserDatasXlsView,
        route_name="userdatas.xls",
        permission="manage",
    )

    config.add_view(
        py3o_view,
        route_name="userdata",
        request_param="action=py3o",
        permission="view",
    )
    config.add_view(
        FileUploadView,
        route_name="userdata",
        renderer='base/formpage.mako',
        permission='manage',
        request_param='action=attach_file',
    )
    # Add the social documents display view
    config.add_route(
        "mydocuments",
        "/mydocuments",
    )
    config.add_view(
        mydocuments_view,
        route_name="mydocuments",
        renderer="mydocuments.mako",
        permission="view",
    )
