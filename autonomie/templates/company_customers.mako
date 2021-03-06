<%doc>
 * Copyright (C) 2012-2013 Croissance Commune
 * Authors:
       * Arezki Feth <f.a@majerti.fr>;
       * Miotte Julien <j.m@majerti.fr>;
       * Pettier Gabriel;
       * TJEBBES Gaston <g.t@majerti.fr>

 This file is part of Autonomie : Progiciel de gestion de CAE.

    Autonomie is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Autonomie is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Autonomie.  If not, see <http://www.gnu.org/licenses/>.
</%doc>

<%inherit file="base.mako"></%inherit>
<%namespace file="/base/pager.mako" import="pager"/>
<%namespace file="/base/pager.mako" import="sortable"/>
<%namespace file="/base/utils.mako" import="table_btn"/>
<%block name='actionmenu'>
## We place the search form in the actionmenu since there are a few fields
    <% request.actionmenu.add(form) %>
    ${request.actionmenu.render(request)|n}
</%block>
<%block name='content'>
<%
## We build the link with the current search arguments
args = request.GET
url = request.route_path('customers.csv', id=request.context.id, _query=args)
%>
<a class='btn btn-default pull-right' href='${url}' ><i class='glyphicon glyphicon-file'></i>Export</a>
<table class="table table-striped table-condensed table-hover">
    <thead>
        <tr>
            <th class="visible-lg">${sortable("Code", "code")}</th>
            <th>${sortable("Entreprise", "name")}</th>
            <th class="visible-lg">${sortable("Nom du contact principal", "contactLastName")}</th>
            <th class="actions">Actions</th>
        </tr>
    </thead>
    <tbody>
        % if records:
            % for customer in records:
                <tr class='tableelement' id="${customer.id}">
                    <% url = request.route_path("customer", id=customer.id) %>
                    <% onclick = "document.location='{url}'".format(url=url) %>
                    <td onclick="${onclick}" class="visible-lg rowlink" >${customer.code}</td>
                    <td onclick="${onclick}" class="rowlink" >${customer.name}</td>
                    <td onclick="${onclick}" class="visible-lg rowlink" >${customer.contactLastName} ${customer.contactFirstName}</td>
                    <td class="actions">
                        % for btn in item_actions:
                            ${btn.render(request, customer)|n}
                        % endfor
                    </td>
                </tr>
            % endfor
        % else:
            <tr>
                <td colspan='6'>
                    Aucun client n'a été référencé pour l'instant
                </td>
            </tr>
        % endif
    </tbody>
</table>
${pager(records)}
</%block>
