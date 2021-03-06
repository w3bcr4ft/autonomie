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
    Administration views
    - config table configuration
    - welcome message
    - logo upload
"""
import logging

from sqlalchemy import desc
from pyramid.httpexceptions import HTTPFound
from autonomie.models.config import (
    Config,
    ConfigFiles,
)
from autonomie.models.tva import (
    Tva,
    Product,
)
from autonomie.models.task.invoice import PaymentMode
from autonomie.models.task import WorkUnit
from autonomie.models.treasury import (
    ExpenseType,
    ExpenseKmType,
    ExpenseTelType,
)
from autonomie.models.activity import (
    ActivityType,
    ActivityMode,
    ActivityAction,
)
from autonomie.models.workshop import WorkshopAction
from autonomie.models.company import (
    Company,
    CompanyActivity,
)
from autonomie.models.user import (
    ZoneOption,
    ZoneQualificationOption,
    StudyLevelOption,
    SocialStatusOption,
    ActivityTypeOption,
    PcsOption,
    PrescripteurOption,
    NonAdmissionOption,
    ParcoursStatusOption,
    MotifSortieOption,
    SocialDocTypeOption,
    CaeSituationOption,
    TypeSortieOption,
)
from autonomie.models.task import PaymentConditions
from autonomie.resources import admin_option_js

from autonomie.models import files
from autonomie.forms.admin import (
    MainConfig,
    get_tva_config_schema,
    PaymentModeConfig,
    WorkUnitConfig,
    ExpenseTypesConfig,
    WorkshopConfigSchema,
    ActivityConfigSchema,
    CAECONFIG,
    get_config_appstruct,
    get_config_dbdatas,
    merge_config_datas,
)
from autonomie.forms.files import get_template_upload_schema
from autonomie.utils.widgets import ViewLink
from js.tinymce import tinymce
from autonomie.views import (
    submit_btn,
    BaseFormView,
    BaseView,
    DisableView,
)
from autonomie.views.admin.tools import (
    get_model_admin_view,
    add_link_to_menu,
)
from autonomie.forms import (
    merge_session_with_post,
)
from autonomie.views.files import (
    FileUploadView,
    FileEditView,
    file_dl_view,
)


log = logging.getLogger(__name__)


UPLOAD_OK_MSG = u"Le modèle de document a bien été ajouté"
EDIT_OK_MSG = u"Le modèle de document a bien été modifié"


def index(request):
    """
        Return datas for the index view
    """
    request.actionmenu.add(
        ViewLink(
            u"Configuration générale",
            path='admin_main',
            title=u"Configuration générale de votre installation d'autonomie"
        )
    )
    request.actionmenu.add(
        ViewLink(
            u"Configuration comptable des produits et TVA collectés",
            path='admin_tva',
            title=u"Configuration des taux de TVA proposés dans les devis et \
factures"
        )
    )
    request.actionmenu.add(
        ViewLink(
            u"Configuration des modes de paiement",
            path="admin_paymentmode",
            title=u"Configuration des modes de paiement des factures"
        )
    )
    request.actionmenu.add(
        ViewLink(
            u"Configuration des conditions de paiement",
            path="admin_payment_conditions",
            title=u"Configuration des conditions de paiement"
        )
    )
    request.actionmenu.add(
        ViewLink(
            u"Configuration des unités de prestation",
            path="admin_workunit",
            title=u"Configuration des unités de prestation proposées \
dans les formulaires"
        )
    )
    request.actionmenu.add(
        ViewLink(
            u"Configuration des notes de frais",
            path="admin_expense",
            title=u"Configuration des types de notes de frais"
        )
    )
    request.actionmenu.add(
        ViewLink(
            u"Configuration comptable du module ventes",
            path="admin_cae",
            title=u"Configuration des différents comptes analytiques de la CAE"
        )
    )
    request.actionmenu.add(
        ViewLink(
            u"Configuration du module accompagnement",
            path="admin_accompagnement",
            title=u"Configuration des types d'activité du module \
accompagnement"
        )
    )
    request.actionmenu.add(
        ViewLink(
            u"Administration de la gestion sociale",
            path='admin_userdatas',
            title=u"Configuration des types pour la gestion sociale",
        )
    )
    request.actionmenu.add(
        ViewLink(
            u"Configuration des domaines d'activité des entreprises",
            path="admin_company_activity",
            title=u"Configuration des domaines d'activité des entreprises"
        )
    )
    return dict(title=u"Administration du site")


def make_enter_point_view(parent_route, views_to_link_to, title=u""):
    """
    Builds a view with links to the views passed as argument

        views_to_link_to

            list of 2-uples (view_obj, route_name) we'd like to link to

        parent_route

            route of the parent page
    """
    def myview(request):
        """
        The dinamycally built view
        """
        request.actionmenu.add(
            ViewLink(
                u"Retour",
                path=parent_route
            )
        )
        for view, route_name, tmpl in views_to_link_to:
            request.actionmenu.add(
                ViewLink(
                    view.title,
                    path=route_name,
                    title=view.title,
                )
            )
        return dict(title=title)
    return myview


def populate_actionmenu(request):
    """
        Add a back to index link
    """
    add_link_to_menu(
        request,
        u"Revenir à l'index",
        path="admin_index",
        title=u"Revenir à l'index de l'administration",
    )


class AdminMain(BaseFormView):
    """
        Main configuration view
    """
    add_template_vars = ('title',)
    title = u"Configuration générale"
    validation_msg = u"La configuration a bien été modifiée"
    schema = MainConfig()
    buttons = (submit_btn,)

    def before(self, form):
        """
            Add the appstruct to the form
        """
        config_dict = self.request.config
        logo = ConfigFiles.get('logo.png')
        appstruct = get_config_appstruct(self.request, config_dict, logo)
        form.set_appstruct(appstruct)
        populate_actionmenu(self.request)
        tinymce.need()

    def submit_success(self, appstruct):
        """
            Insert config informations into database
        """
        # la table config étant un stockage clé valeur
        # le merge_session_with_post ne peut être utilisé
        logo = appstruct['site'].pop('logo', None)
        if logo:
            ConfigFiles.set('logo.png', logo)
            self.request.session.pop('substanced.tempstore')
            self.request.session.changed()

        dbdatas = self.dbsession.query(Config).all()
        appstruct = get_config_dbdatas(appstruct)
        dbdatas = merge_config_datas(dbdatas, appstruct)
        for dbdata in dbdatas:
            self.dbsession.merge(dbdata)
        self.dbsession.flush()
        self.request.session.flash(self.validation_msg)
        return HTTPFound(self.request.route_path("admin_main"))


class AdminTva(BaseFormView):
    """
        Tva administration view
        Set tvas used in invoices, estimations and cancelinvoices
    """
    title = u"Configuration des taux de TVA"
    validation_msg = u"Les taux de TVA ont bien été modifiés"
    schema = get_tva_config_schema()
    buttons = (submit_btn,)

    def before(self, form):
        """
            Add appstruct to the current form object
        """
        appstruct = []
        for tva in Tva.query().all():
            struct = tva.appstruct()
            struct['products'] = [
                product.appstruct() for product in tva.products
            ]
            appstruct.append(struct)

        form.set_appstruct({'tvas': appstruct})
        populate_actionmenu(self.request)
        log.debug("AdminTva struct: %s", appstruct)

    @staticmethod
    def get_remaining_prod_ids(appstruct):
        """
            return id of products remaining in the submitted config
        """
        ids = []
        for tva in appstruct['tvas']:
            ids.extend([
                product['id'] for product in tva['products'] if 'id' in product
            ])
        return ids

    @staticmethod
    def get_remaining_tva_ids(appstruct):
        """
            Return ids of tva remaining in the submitted config
        """
        return [tva['id'] for tva in appstruct['tvas'] if 'id' in tva]

    def disable_elements(self, factory, ids):
        """
            Disable elements of type "factory" that are not in the ids list
        """
        for element in factory.query(include_inactive=True).all():
            if element.id not in ids:
                element.active = False
                self.dbsession.merge(element)

    def submit_success(self, appstruct):
        """
            fired on submit success, set Tvas
        """
        # First we disable the elements that are no longer part of the
        # configuration
        self.disable_elements(Product, self.get_remaining_prod_ids(appstruct))
        self.disable_elements(Tva, self.get_remaining_tva_ids(appstruct))
        self.dbsession.flush()

        for data in appstruct['tvas']:
            products = data.pop('products')
            if 'id' in data:
                tva = Tva.get(data['id'])
                merge_session_with_post(tva, data)
                tva = self.dbsession.merge(tva)
            else:
                tva = Tva()
                merge_session_with_post(tva, data)
                self.dbsession.add(tva)

            for prod in products:
                if 'id' in prod:
                    product = Product.get(prod['id'])
                    product.tva = tva
                    merge_session_with_post(product, prod)
                    self.dbsession.merge(product)
                else:
                    product = Product()
                    merge_session_with_post(product, prod)
                    product.tva = tva
                    self.dbsession.add(product)
        self.request.session.flash(self.validation_msg)
        return HTTPFound(self.request.route_path("admin_tva"))


class AdminPaymentMode(BaseFormView):
    """
        Payment Mode administration view
        Allows to set different payment mode
    """
    title = u"Configuration des modes de paiement"
    validation_msg = u"Les modes de paiement ont bien été modifiés"
    schema = PaymentModeConfig()
    buttons = (submit_btn,)

    def before(self, form):
        """
            Add appstruct to the current form object
        """
        appstruct = [mode.label for mode in PaymentMode.query()]
        form.set_appstruct({'paymentmodes': appstruct})
        populate_actionmenu(self.request)

    def submit_success(self, appstruct):
        """
            handle successfull payment mode configuration
        """
        for mode in PaymentMode.query():
            self.dbsession.delete(mode)
        for data in appstruct['paymentmodes']:
            mode = PaymentMode(label=data)
            self.dbsession.add(mode)
        self.request.session.flash(self.validation_msg)
        return HTTPFound(self.request.route_path("admin_paymentmode"))


class AdminWorkUnit(BaseFormView):
    """
        Work Unit administration view
        Allows to configure custom unities
    """
    title = u"Configuration des unités de prestation"
    validation_msg = u"Les unités de prestation ont bien été modifiées"
    schema = WorkUnitConfig()
    buttons = (submit_btn,)

    def before(self, form):
        """
            Add appstruct to the current form object
        """
        appstruct = [mode.label for mode in WorkUnit.query()]
        form.set_appstruct({'workunits': appstruct})
        populate_actionmenu(self.request)

    def submit_success(self, appstruct):
        """
            Handle successfull work unit configuration
        """
        for unit in WorkUnit.query():
            self.dbsession.delete(unit)
        for data in appstruct['workunits']:
            unit = WorkUnit(label=data)
            self.dbsession.add(unit)
        self.request.session.flash(self.validation_msg)
        return HTTPFound(self.request.route_path("admin_workunit"))


class AdminExpense(BaseFormView):
    """
        Expense administration view
        Allows to configure expense types and codes
    """
    title = u"Configuration des notes de frais"
    validation_msg = u"Les différents paramètres des notes de frais \
ont été configurés"
    schema = ExpenseTypesConfig()
    buttons = (submit_btn,)
    factories = {'expenses': (ExpenseType, 'expense'),
                 'expenseskm': (ExpenseKmType, 'expensekm'),
                 'expensestel': (ExpenseTelType, 'expensetel')}

    def _get_config_key(self, rel_keyname):
        return rel_keyname + "_ndf"

    def before(self, form):
        """
        Add appstruct to the current form object
        """
        appstruct = {}

        for key in ('code_journal', 'compte_cg'):
            cfg_key = self._get_config_key(key)
            appstruct[key] = self.request.config.get(cfg_key, '')

        for key, (factory, polytype) in self.factories.items():
            query = factory.query().filter(factory.type == polytype)
            query = query.filter(factory.active == True)
            appstruct[key] = [e.appstruct() for e in query]

        form.set_appstruct(appstruct)
        populate_actionmenu(self.request)

    def get_all_ids(self, appstruct):
        """
        Return the ids of the options still present in the submitted form
        """
        ids = []
        for key in self.factories:
            ids.extend([data['id'] for data in appstruct[key] if 'id' in data])
        return ids

    def _get_actual_config_obj(self, config_key):
        """
        Return the actual configured compte_cg object
        """
        return Config.get(config_key)

    def _set_config_value(self, appstruct, config_key, appstruct_key):
        """
        Set a config value
        :param appstruct: the form submitted values
        :param config_key: The name of the configuration key
        :param appstruct_key: The name of the key in the appstruct
        """
        cfg_obj = self._get_actual_config_obj(config_key)
        value = appstruct.pop(appstruct_key, None)

        if value:
            if cfg_obj is None:
                cfg_obj = Config(name=config_key, value=value)
                self.dbsession.add(cfg_obj)

            else:
                cfg_obj.value = value
                self.dbsession.merge(cfg_obj)

        log.debug(u"Setting the new {0} : {1}".format(config_key, value))

    def submit_success(self, appstruct):
        """
        Handle successfull expense configuration
        :param appstruct: submitted datas
        """
        all_ids = self.get_all_ids(appstruct)

        # We delete the elements that are no longer in the appstruct
        for (factory, polytype) in self.factories.values():
            for element in factory.query().filter(factory.type == polytype):
                if element.id not in all_ids:
                    element.active = False
                    self.dbsession.merge(element)
        self.dbsession.flush()

        for key in ('code_journal', 'compte_cg'):
            cfg_key = self._get_config_key(key)
            self._set_config_value(appstruct, cfg_key, key)

        for key, (factory, polytype) in self.factories.items():
            for data in appstruct[key]:
                if data.get('id') is not None:
                    type_ = factory.get(data['id'])
                    merge_session_with_post(type_, data)
                    self.dbsession.merge(type_)
                else:
                    type_ = factory()
                    merge_session_with_post(type_, data)
                    self.dbsession.add(type_)

        self.request.session.flash(self.validation_msg)
        return HTTPFound(self.request.route_path("admin_expense"))


class BaseAdminActivities(BaseFormView):
    """
        Activity types config
    """
    title = u"Configuration du module accompagnement"
    validation_msg = u"Le module a bien été configuré"
    buttons = (submit_btn,)

    def populate_actionmenu(self, request):
        """
            Add a back to index link
        """
        add_link_to_menu(
            request,
            u"Revenir en arrière",
            path="admin_accompagnement",
            title=u"Revenir à la page précédente",
        )

    def _add_pdf_img_to_appstruct(self, data_type, appstruct):
        for file_type in ("header_img", "footer_img"):
            file_name = "%s_%s.png" % (data_type, file_type)
            file_model = ConfigFiles.get(file_name)
            if file_model is not None:
                appstruct[file_type] = {
                    'uid': file_model.id,
                    'filename': file_model.name,
                    'preview_url': self.request.route_url(
                        'public',
                        name=file_name,
                    )
                }

    def _recursive_action_appstruct(self, actions):
        appstruct = []
        for action in actions:
            action_appstruct = action.appstruct()
            if action.children is not None:
                action_appstruct['children'] = self._recursive_action_appstruct(
                    action.children
                )
            appstruct.append(action_appstruct)
        return appstruct

    def get_edited_elements(self, appstruct, key=None):
        """
        Return a dict id:data for the elements that are edited (with an id)
        """
        if key is not None:
            appstruct = appstruct.get(key, {})
        return dict((data['id'], data) for data in appstruct if 'id' in data)

    def get_submitted_modes(self, appstruct):
        """
        Return the modes that have been submitted
        """
        return [data['label'] for data in appstruct['modes']]

    def disable_types(self, appstruct):
        """
        Disable types that are no longer used
        """
        edited_types = self.get_edited_elements(appstruct, "types")

        for element in ActivityType.query():
            if element.id not in edited_types.keys():
                element.active = False
                self.dbsession.merge(element)

    def recursive_collect_ids(self, appstruct, key=None):
        result = []
        if key is not None:
            appstruct = appstruct.get(key, [])
        for local_appstruct in appstruct:
            if 'children' in local_appstruct.keys():
                children_ids = self.recursive_collect_ids(
                    local_appstruct,
                    'children'
                )
                result.extend(children_ids)
            if 'id' in local_appstruct:
                result.append(local_appstruct['id'])
        return result

    def disable_actions(self, appstruct, factory):
        """
        Disable actions that are not active anymore
        """
        # on récupère les ids des actions encore dans la config
        ids = self.recursive_collect_ids(appstruct, 'actions')
        from sqlalchemy import not_

        for element in factory.query().filter(
            not_(getattr(factory, 'id').in_(ids))
        ):
            element.active = False
            self.dbsession.merge(element)

    def delete_modes(self, appstruct):
        """
        Delete modes that are no longer used

        Return modes that have to be added
        """
        all_modes = self.get_submitted_modes(appstruct)
        for element in ActivityMode.query():
            if element.label not in all_modes:
                self.dbsession.delete(element)
            else:
                # Remove it from the submitted list so we don't insert it again
                all_modes.remove(element.label)
        return all_modes

    def _add_or_edit(self, datas, factory):
        """
        Add or edit an element of the given factory
        """
        if 'id' in datas:
            element = factory.get(datas['id'])
            merge_session_with_post(element, datas)
            element = self.dbsession.merge(element)
        else:
            element = factory()
            merge_session_with_post(element, datas)
            self.dbsession.add(element)
        return element

    def add_types(self, appstruct):
        """
        Add/edit the types
        """
        for data in appstruct["types"]:
            self._add_or_edit(data, ActivityType)

    def add_modes(self, new_modes):
        """
        Add new modes
        modes are not relationships so we don't need to keep them
        """
        for mode in new_modes:
            new_mode_obj = ActivityMode(label=mode)
            self.dbsession.add(new_mode_obj)

    def add_actions(self, appstruct, key, factory):
        """
        Add recursively new actions (with parent-child relationship)
        """
        result = []
        for action_appstruct in appstruct[key]:
            # On remplace les noeuds children par des instances
            if 'children' in action_appstruct:
                action_appstruct['children'] = self.add_actions(
                    action_appstruct,
                    'children',
                    factory
                )
            result.append(self._add_or_edit(action_appstruct, factory))
        return result

    def store_pdf_conf(self, appstruct, data_type):
        """
        Store the pdf configuration for the given type

        :param dict appstruct: The datas in which we will find the pdf
        configuration
        :param str data_type: activity/workshop
        """
        pdf_appstruct = appstruct
        for file_type in ("header_img", "footer_img"):
            file_datas = pdf_appstruct.get(file_type)
            if file_datas:
                file_name = "%s_%s.png" % (data_type, file_type)
                ConfigFiles.set(file_name, file_datas)

        Config.set(
            "%s_footer" % data_type,
            pdf_appstruct.get('footer', '')
        )


class AdminActivities(BaseAdminActivities):
    """
    Activities Admin view
    """
    title = u"Configuration du module de Rendez-vous"
    schema = ActivityConfigSchema(title=u"")

    def before(self, form):
        query = ActivityType.query()
        types = query.filter_by(active=True)

        modes = ActivityMode.query()

        query = ActivityAction.query()
        query = query.filter_by(parent_id=None)
        actions = query.filter_by(active=True)

        activity_appstruct = {
            'footer': self.request.config.get("activity_footer", ""),
            'types': [type_.appstruct() for type_ in types],
            'modes': [mode.appstruct() for mode in modes],
            'actions': self._recursive_action_appstruct(actions)
        }
        self._add_pdf_img_to_appstruct('activity', activity_appstruct)
        form.set_appstruct(activity_appstruct)
        self.populate_actionmenu(self.request)

    def submit_success(self, activity_appstruct):
        """
            Handle successfull expense configuration
        """
        self.store_pdf_conf(activity_appstruct, 'activity')
        # We delete the elements that are no longer in the appstruct
        self.disable_types(activity_appstruct)
        self.disable_actions(activity_appstruct, ActivityAction)
        new_modes = self.delete_modes(activity_appstruct)
        self.dbsession.flush()

        self.add_types(activity_appstruct)
        self.add_actions(activity_appstruct, "actions", ActivityAction)
        self.add_modes(new_modes)

        self.request.session.flash(self.validation_msg)
        return HTTPFound(
            self.request.route_path("admin_accompagnement")
        )


class AdminWorkshop(BaseAdminActivities):
    """
    Workshops administration views
    """
    title = u"Administration du module Atelier"
    schema = WorkshopConfigSchema(title=u"")

    def before(self, form):
        """
            Add appstruct to the current form object
        """
        query = WorkshopAction.query()
        query = query.filter_by(parent_id=None)
        actions = query.filter_by(active=True)

        workshop_appstruct = {
            'footer': self.request.config.get("workshop_footer", ""),
            'actions': self._recursive_action_appstruct(actions)
        }

        form.set_appstruct(workshop_appstruct)
        self.populate_actionmenu(self.request)

    def submit_success(self, workshop_appstruct):
        """
            Handle successfull expense configuration
        """

        self.store_pdf_conf(workshop_appstruct, 'workshop')
        # We delete the elements that are no longer in the appstruct
        self.disable_actions(workshop_appstruct, WorkshopAction)
        self.dbsession.flush()

        self.add_actions(workshop_appstruct, "actions", WorkshopAction)

        self.request.session.flash(self.validation_msg)
        return HTTPFound(
            self.request.route_path("admin_accompagnement")
        )


class AdminCae(BaseFormView):
    """
        Cae information configuration
    """
    title = u"Configuration comptable du module ventes"
    validation_msg = u"Les informations ont bien été enregistrées"
    schema = CAECONFIG
    buttons = (submit_btn, )

    def before(self, form):
        """
            Add the appstruct to the form
        """
        appstruct = {}
        for key, value in self.request.config.items():
            if key.startswith('sage'):
                appstruct.setdefault('sage_export', {})[key] = value
            else:
                appstruct[key] = value

        form.set_appstruct(appstruct)
        populate_actionmenu(self.request)

    def submit_success(self, appstruct):
        """
            Insert config informations into database
        """
        # la table config étant un stockage clé valeur
        # le merge_session_with_post ne peut être utilisé
        dbdatas = Config.query().all()

        log.debug(u"Cae configuration submission")
        log.debug(appstruct)

        new_dbdatas = merge_config_datas(dbdatas, appstruct)
        for dbdata in new_dbdatas:
            log.debug(dbdata.name)
            if dbdata in dbdatas:
                self.dbsession.merge(dbdata)
            else:
                self.dbsession.add(dbdata)
            # If we set the contribution_cae value, we want it to be the default
            # for every company that has no contribution value set
            if dbdata.name == 'contribution_cae':
                for comp in Company.query():
                    if comp.contribution is None:
                        comp.contribution = dbdata.value
                        self.dbsession.merge(comp)
        self.dbsession.flush()
        self.request.session.flash(self.validation_msg)
        return HTTPFound(self.request.route_path("admin_cae"))


class TemplateUploadView(FileUploadView):
    title = u"Administrer les modèles de documents"
    factory = files.Template
    schema = get_template_upload_schema()
    valid_msg = UPLOAD_OK_MSG

    def before(self, form):
        come_from = self.request.referrer
        log.debug(u"Coming from : %s" % come_from)

        appstruct = {
            'come_from': come_from
        }
        form.set_appstruct(appstruct)
        add_link_to_menu(
            self.request,
            u"Revenir à la liste",
            "templates",
            "")


class TemplateEditView(FileEditView):
    valid_msg = u"Le modèle de document a bien été modifié"
    factory = files.Template
    schema = get_template_upload_schema()
    valid_msg = EDIT_OK_MSG

    def before(self, form):
        FileEditView.before(self, form)
        add_link_to_menu(
            self.request,
            u"Revenir à la liste",
            "templates",
            "",
        )


class TemplateList(BaseView):
    """
    Listview of templates
    """
    title = u"Modèles de documents"

    def __call__(self):
        add_link_to_menu(
            self.request,
            u"Retour",
            path="admin_userdatas",
            title=u"Retour à l'administration de la gestion sociale"
        )

        templates = files.Template.query()\
            .order_by(desc(files.Template.active))\
            .all()
        return dict(templates=templates, title=self.title)


def get_all_userdatas_views():
    """
    Return view_class, route_name for all option configuration views in the
    userdatas module
    """
    yield get_model_admin_view(
        CaeSituationOption,
        js_requirements=admin_option_js,
    )
    for model in (
        ZoneOption,
        ZoneQualificationOption,
        StudyLevelOption,
        SocialStatusOption,
        ActivityTypeOption,
        PcsOption,
        PrescripteurOption,
        NonAdmissionOption,
        ParcoursStatusOption,
        MotifSortieOption,
        SocialDocTypeOption,
        TypeSortieOption,
    ):
        yield get_model_admin_view(model)
    yield TemplateList, 'templates', '/admin/templates.mako'


class TemplateDisableView(DisableView):
    enable_msg = u"Le template a bien été activé"
    disable_msg = u"Le template a bien été désactivé"
    redirect_route = "templates"


def console_view(request):
    """
    """
    for label, route in (
        (u"Historique mail salaire", 'mailhistory',),
        (u"Tâches celery", 'jobs',),
    ):
        request.actionmenu.add(
            ViewLink(label, path=route, title=label)
        )
    return dict(title=u"Console de supervision")


def admin_accompagnement_index_view(request):
    for label, route in (
        (u"Retour", "admin_index",),
        (u"Configuration du module Rendez-vous", "admin_activity"),
        (u"Configuration du module Atelier", "admin_workshop",),
        (u"Configuration du module Compétences", "admin_competences",),
    ):
        request.actionmenu.add(
            ViewLink(label, path=route, title=label)
        )
    return dict(title=u"Administration du module accompagnement")


def includeme(config):
    """
        Add module's views
    """
    # Administration routes
    config.add_route("admin_index", "/admin")
    config.add_route("admin_main", "/admin/main")
    config.add_route("admin_tva", "/admin/tva")
    config.add_route("admin_paymentmode", "admin/paymentmode")
    config.add_route("admin_workunit", "admin/workunit")
    config.add_route("admin_expense", "admin/expense")
    config.add_route("admin_accompagnement", "admin/accompagnement")
    config.add_route("admin_activity", "admin/activity")
    config.add_route("admin_workshop", "admin/workshop")
    config.add_route("admin_cae", "admin/cae")

    config.add_view(
        index,
        route_name='admin_index',
        renderer='admin/index.mako',
        permission='admin',
    )

    config.add_view(
        AdminMain,
        route_name="admin_main",
        renderer="admin/main.mako",
        permission='admin',
    )

    config.add_view(
        AdminTva,
        route_name='admin_tva',
        renderer="admin/main.mako",
        permission='admin',
    )

    config.add_view(
        AdminPaymentMode,
        route_name='admin_paymentmode',
        renderer="admin/main.mako",
        permission='admin',
    )

    for model in (PaymentConditions, CompanyActivity):
        view, route_name, tmpl = get_model_admin_view(
            model,
            r_path="admin_index",
        )
        config.add_route(route_name, "admin/" + route_name)
        config.add_view(
            view,
            route_name=route_name,
            renderer=tmpl,
            permission="admin",
        )

    config.add_view(
        AdminWorkUnit,
        route_name='admin_workunit',
        renderer="admin/main.mako",
        permission='admin',
    )

    config.add_view(
        AdminExpense,
        route_name='admin_expense',
        renderer="admin/main.mako",
        permission='admin',
    )

    config.add_view(
        admin_accompagnement_index_view,
        route_name='admin_accompagnement',
        renderer="admin/index.mako",
        permission='admin',
    )

    config.add_view(
        AdminActivities,
        route_name='admin_activity',
        renderer="admin/main.mako",
        permission='admin',
    )

    config.add_view(
        AdminWorkshop,
        route_name='admin_workshop',
        renderer="admin/main.mako",
        permission='admin',
    )

    config.add_view(
        AdminCae,
        route_name='admin_cae',
        renderer="admin/main.mako",
        permission="admin",
    )

    # User Datas view configuration
    config.add_route("admin_userdatas", "admin/userdatas")

    all_option_views = list(get_all_userdatas_views())
    for view, route_name, tmpl in all_option_views:
        config.add_route(route_name, "admin/" + route_name)
        config.add_view(
            view,
            route_name=route_name,
            renderer=tmpl,
            permission="admin",
        )

    config.add_route(
        'template',
        'admin/templates/{id}',
        traverse="templates/{id}",
    )

    config.add_view(
        TemplateDisableView,
        route_name='template',
        request_param='action=disable',
        permission='admin',
    )

    config.add_view(
        file_dl_view,
        route_name='template',
        permission='admin',
    )

    config.add_view(
        TemplateEditView,
        route_name='template',
        renderer='admin/template_edit.mako',
        request_param='action=edit',
        permission='admin',
    )

    config.add_view(
        TemplateUploadView,
        route_name='templates',
        renderer='admin/template_add.mako',
        request_param='action=new',
        permission='admin',
    )

    config.add_view(
        make_enter_point_view(
            'admin_index',
            all_option_views,
            u"Administration de la gestion sociale"
        ),
        route_name="admin_userdatas",
        renderer='admin/index.mako',
        permission="admin",
    )

    # Hidden console view
    config.add_route("admin_console", "admin_console/")
    config.add_view(
        console_view,
        route_name="admin_console",
        renderer="admin/index.mako",
        permission="admin",
    )
