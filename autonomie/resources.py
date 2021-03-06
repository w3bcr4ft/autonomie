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
    Handle static libraries inside autonomie with the help of fanstatic
"""
from fanstatic import Group
from fanstatic import Library
from fanstatic import Resource
from js.bootstrap import (
    bootstrap,
)
from js.jquery import jquery
from js.jqueryui import effects_highlight
from js.jqueryui import effects_shake
from js.jqueryui import ui_dialog
from js.jqueryui import ui_sortable
from js.jqueryui import ui_datepicker_fr
from js.jqueryui import bootstrap as jqueryui_bootstrap_theme
from js.jquery_timepicker_addon import timepicker_js
from js.jquery_form import jquery_form
from js.jquery_qunit import jquery_qunit
from js.select2 import select2

lib_autonomie = Library("fanstatic", "static")

# ui_dialog.depends.add(bootstrap_js)


def get_resource(filepath, minified=None, depends=None):
    """
    Return a resource object included in autonomie
    """
    return Resource(
        lib_autonomie,
        filepath,
        minified=minified,
        depends=depends,
    )


def get_main_group():
    """
    Return the main resource Group that will be used on all pages
    """
    # UnPackaged external libraries
    font_awesome_css = get_resource("css/font-awesome.min.css")
    underscore = get_resource(
        "js/vendors/underscore.js",
        minified="js/vendors/underscore-min.js"
    )

    main_js = get_resource(
        "js/main.js",
        depends=[ui_dialog, ui_sortable, underscore]
    )
    main_css = get_resource(
        "css/main.css",
        depends=[
            bootstrap,
            jqueryui_bootstrap_theme,
            font_awesome_css,
        ]
    )

    _date = get_resource("js/date.js", depends=[timepicker_js])
    _dom = get_resource("js/dom.js", depends=[jquery])
    _math = get_resource("js/math.js")
    js_tools = Group([_dom, _math, _date])

    return Group([
        main_js,
        main_css,
        js_tools,
        jquery_form,
        ui_datepicker_fr,
    ])


main_group = get_main_group()


def get_module_group():
    """
    Return main libraries used in custom modules (backbone marionette and
    handlebar stuff)

    NB : depends on the main_group
    """
    handlebar = get_resource("js/vendors/handlebars.runtime.js")
    backbone = get_resource(
        "js/vendors/backbone.js",
        minified="js/vendors/backbone-min.js",
        depends=[main_group],
    )
    backbone_marionnette = get_resource(
        "js/vendors/backbone.marionette.js",
        minified="js/vendors/backbone.marionette.min.js",
        depends=[backbone]
    )
    # Bootstrap form validation stuff
    backbone_validation = get_resource(
        "js/vendors/backbone-validation.js",
        minified="js/vendors/backbone-validation-min.js",
        depends=[backbone]
    )
    backbone_validation_bootstrap = get_resource(
        "js/backbone-validation-bootstrap.js",
        depends=[backbone_validation]
    )
    # Popup object
    backbone_popup = get_resource(
        "js/backbone-popup.js",
        depends=[backbone_marionnette]
    )
    # Some specific tuning
    backbone_tuning = get_resource(
        "js/backbone-tuning.js",
        depends=[backbone_marionnette, handlebar]
    )
    # The main templates
    main_templates = get_resource(
        "js/template.js",
        depends=[handlebar]
    )
    # Messages
    message_js = get_resource(
        "js/message.js",
        depends=[handlebar]
    )
    return Group(
        [
            backbone_marionnette,
            backbone_validation_bootstrap,
            backbone_tuning,
            backbone_popup,
            main_templates,
            effects_highlight,
            effects_shake,
            message_js,
        ]
    )


module_libs = get_module_group()


def get_module_resource(module, tmpl=False, extra_depends=()):
    """
    Return a resource group (or a single resource) for the given module

    static/js/<module>.js and static/js/templates/<module>.js

    :param str module: the name of a js file
    :param bool tmpl: is there an associated tmpl
    :param extra_depends: extra dependencies
    """
    depends = [module_libs]
    depends.extend(extra_depends)
    if tmpl:
        tmpl_resource = get_resource(
            "js/templates/%s.js" % module,
            depends=[module_libs]
        )
        depends.append(tmpl_resource)

    return get_resource(
        "js/%s.js" % module,
        depends=depends
    )


duplicate = get_module_resource("duplicate")
discount = get_module_resource("discount")
address = get_module_resource("address")
tva = get_module_resource("tva")

task = get_module_resource(
    "task",
    tmpl=True,
    extra_depends=[
        address,
        discount,
        duplicate,
        tva,
    ]
)
task_list_js = get_module_resource("task_list")
event_list_js = get_module_resource('event_list')

job_js = get_module_resource("job", tmpl=True)

expense_js = get_module_resource("expense", tmpl=True)
statistics_js = get_module_resource(
    'statistics',
    tmpl=True,
    extra_depends=[select2]
)
competence_js = get_module_resource(
    'competence',
    tmpl=True,
    extra_depends=[select2]
)
holiday_js = get_module_resource("holiday", tmpl=True)
admin_option_js = get_module_resource("admin_option")
commercial_js = get_module_resource("commercial")


# Test tools
def get_test_resource():
    res = []
    for i in ('math', 'date', 'dom', 'task'):
        res.append(
            get_resource(
                "js/tests/test_%s.js" % i,
                depends=(jquery_qunit, main_group, task)
            )
        )
    return Group(res)


test_js = get_test_resource()

# File upload page js requirements
fileupload_js = get_resource(
    "js/fileupload.js",
    depends=[main_group],
)

# Chart tools
d3_js = get_resource("js/vendors/d3.v3.js", minified="js/vendors/d3.v3.min.js")
radar_chart_js = get_resource("js/vendors/radar-chart.js", depends=[d3_js])
radar_chart_css = get_resource(
    "css/radar-chart.css",
    minified="css/radar-chart.min.css"
)
competence_radar_js = get_module_resource(
    "competence_radar", extra_depends=(radar_chart_js, radar_chart_css,)
)
