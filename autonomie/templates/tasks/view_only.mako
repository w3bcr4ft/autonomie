<%doc>
    Base template for task readonly display
</%doc>
<%inherit file="/base.mako"></%inherit>
<%block name='content'>
<div class='container' style='overflow:hidden'>
    <div class='well'>
        <p>
            <span class="label label-important"><i class='icon-white icon-play'></i></span>
            %if task.statusPersonAccount  is not UNDEFINED and task.statusPersonAccount:
                <strong>${api.format_status(task)}</strong>
            %else:
                <strong>Aucune information d'historique ou de statut n'a pu être retrouvée.</strong>
            %endif
        </p>
        %if not task.is_editable():
            <p>
                % if task.is_waiting():
                    Vous ne pouvez plus modifier ce document car il est en attente de validation.
                % else:
                    Vous ne pouvez plus modifier ce document car il a déjà été validé.
                    % if hasattr(task, 'officialNumber'):
                        Il porte le numéro <b>${task.officialNumber}</b>.
                    % endif
                % endif
            </p>
        %elif task.is_waiting():
            <p>
                Vous ne pouvez plus modifier ce document car il est en attente de validation.
            </p>
        % endif
        % if task.is_invoice():
            % if hasattr(task, 'estimation') and task.estimation:
                <p>
                    Cette facture fait référence au devis : <a href="${request.route_path('estimation', id=task.estimation.id)}">${task.estimation.number}</a>
                </p>
            % endif
            % if hasattr(task, 'cancelinvoice') and task.cancelinvoice:
                <p>
                    L'avoir : <a href="${request.route_path('cancelinvoice', id=task.cancelinvoice.id)}">${task.cancelinvoice.number}</a> a été généré depuis cette facture.
                </p>
            % endif
        % elif task.is_estimation():
            % if hasattr(task, 'invoices') and task.invoices:
                <p>
                    Les factures suivantes ont été générées depuis ce devis :
                    <ul class='unstyled'>
                        % for invoice in task.invoices:
                            <li>
                                <a href="${request.route_path('invoice', id=invoice.id)}">${invoice.number}</a>
                            </li>
                        % endfor
                    </ul>
                </p>
            % endif
        % elif task.is_cancelinvoice():
            % if hasattr(task, 'invoice') and task.invoice:
                <p>
                    Cet avoir est lié à la facture : <a href="${request.route_path('invoice', id=task.invoice.id)}">${task.invoice.officialNumber}</a>
                </p>
            % endif
        %endif

        % if hasattr(task, "statusComment") and task.statusComment:
            <b>Communication CAE-Entrepreneur</b>
            <p>
                ${task.statusComment}
            </p>
        % endif
        % if hasattr(task, "payments"):
            %if task.payments:
                Paiement reçu :
                <ul>
                % for payment in task.payments:
                    <li>${api.format_amount(payment.amount)|n} € le ${api.format_date(payment.date)} (${api.format_paymentmode(payment.mode)}) </li>
                % endfor
                </ul>
            % endif
        % endif
    </div>
            % if task.is_estimation():
                <% route = request.route_path('estimation', id=task.id, _query=dict(action='status')) %>
            % elif task.is_invoice():
                <% route = request.route_path('invoice', id=task.id, _query=dict(action='status')) %>
            % else:
                <% route = request.route_path('cancelinvoice', id=task.id, _query=dict(action='status')) %>
            % endif
            <div class="well">
            <form id="deform" class="deform"
            accept-charset="utf-8"
            enctype="multipart/form-data"
            method="POST"
            action="${route}">
            % for button in submit_buttons:
                ${button.render(request)|n}
            % endfor
        </form>
    </div>
    <div style='border:1px solid #888'>
        ${html_datas|n}
    </div>
</div>
</%block>
