# -*- coding: utf-8 -*-
# * File Name : test_models_tasks.py
#
# * Copyright (C) 2010 Gaston TJEBBES <g.t@majerti.fr>
# * Company : Majerti ( http://www.majerti.fr )
#
#   This software is distributed under GPLV3
#   License: http://www.gnu.org/licenses/gpl-3.0.txt

#
# * Creation Date : 27-07-2012
# * Last Modified :
#
# * Project :
#
"""
    Test Documents (Tasks):
        Estimations
        Invoices
        CancelInvoices
        ManualInvoices
"""

import datetime
from zope.interface.verify import verifyObject
from mock import MagicMock
from pyramid import testing
from .base import BaseTestCase
from .base import BaseViewTest

from autonomie.models.task import Task
from autonomie.models.task import Estimation
from autonomie.models.task import Invoice
from autonomie.models.task import CancelInvoice
from autonomie.models.task import ManualInvoice
from autonomie.models.task import EstimationLine
from autonomie.models.task import InvoiceLine
from autonomie.models.task import PaymentLine
from autonomie.models.task import CancelInvoiceLine
from autonomie.models.task import DiscountLine
from autonomie.models.task import Payment
from autonomie.models.task.states import record_payment
from autonomie.models.task.compute import TaskCompute
from autonomie.models.task.interfaces import ITask
from autonomie.models.task.interfaces import IValidatedTask
from autonomie.models.task.interfaces import IPaidTask
from autonomie.models.task.interfaces import IInvoice

from autonomie.models.user import User
from autonomie.models.project import Project
from autonomie.models.project import Phase

from autonomie.exception import Forbidden

TASK = dict(name=u"Test task",
                 CAEStatus="draft",
                 taskDate=datetime.date.today(),
                 statusDate=datetime.date.today(),
                 description=u"Test task description")

USER = dict(id=2,
            login=u"test_user1",
            firstname=u"user1_firstname",
            lastname=u"user1_lastname")

USER2 = dict(id=3, login=u"test_user2")

PROJECT = dict(id=1, name=u'project1', code=u"PRO1", company_id=1,
        client_id=1)
CLIENT = dict(id=1, name=u"client1", code=u"CLI1", company_id=1)

ESTIMATION = dict(phase_id=1,
                project_id=1,
                name=u"Devis 2",
                sequenceNumber=2,
                CAEStatus="draft",
                course="0",
                displayedUnits="1",
                expenses=1500,
                deposit=20,
                exclusions=u"Notes",
                paymentDisplay=u"ALL",
                paymentConditions=u"Conditions de paiement",
                taskDate=datetime.date(2012, 12, 10), #u"10-12-2012",
                description=u"Description du devis",
                manualDeliverables=1,
                statusComment=u"Aucun commentaire",
                number=u"estnumber")
INVOICE = dict(phase_id=1,
                project_id=1,
                owner_id=2,
                statusPerson=2,
                name=u"Facture 2",
                sequenceNumber=2,
                CAEStatus="draft",
                course="0",
                displayedUnits="1",
                expenses=1500,
                deposit=20,
                paymentConditions=u"Conditions de paiement",
                taskDate=datetime.date(2012, 12, 10), #u"10-12-2012",
                description=u"Description de la facture",
                statusComment=u"Aucun commentaire",
                number=u"invoicenumber")
CANCELINVOICE = dict(phase_id=1,
                project_id=1,
                owner_id=2,
                statusPerson=2,
                name=u"Avoir 2",
                sequenceNumber=2,
                CAEStatus="draft",
                course="0",
                displayedUnits="1",
                expenses=1500,
                paymentConditions=u"Conditions de paiement",
                taskDate=datetime.date(2012, 12, 10), #u"10-12-2012",
                description=u"Description de l'avoir",
                statusComment=u"Aucun commentaire",
                number=u"cancelinvoicenumber")
LINES = [{'description':u'text1',
          'cost':10025,
           'tva':1960,
          'unity':'DAY',
          'quantity':1.25,
          'rowIndex':1},
         {'description':u'text2',
          'cost':7500,
           'tva':1960,
          'unity':'month',
          'quantity':3,
          'rowIndex':2},
         {'description':u'text3',
          'cost':-5200,
           'tva':1960,
          "quantity":1,
          "unity":"DAY",
          "rowIndex":3,}]

PAYMENT_LINES = [{'description':u"Début",
                  "paymentDate":datetime.date(2012, 12, 12),
                  "amount":1000,
                  "rowIndex":1},
                 {'description':u"Milieu",
                  "paymentDate":datetime.date(2012, 12, 13),
                  "amount":1000, "rowIndex":2},
                 {'description':u"Fin",
                  "paymentDate":datetime.date(2012, 12, 14),
                  "amount":150,
                  "rowIndex":3}]

DISCOUNTS = [{'description':u"Remise à 19.6",
              'amount':2000,
              'tva':1960}]

PAYMENTS = [
            {'amount':1500, 'mode':'CHEQUE'},
            {'amount':1895, 'mode':'CHEQUE'},
            ]

# Values:
#         the money values are represented *100
#
# Rounding rules:
#         TVA, total_ttc and deposit are rounded (total_ht is not)

# Lines total should accept until 4 elements after the '.'(here they are *100)
# so it fits the limit case
#
# Line totals should be floats (here they are *100)
EST_LINES_TOTAL_HT = (12531.25, 22500, -5200)
EST_LINES_TVAS = (2456.125, 4410, -1019.2)

LINES_TOTAL_HT = sum(EST_LINES_TOTAL_HT)
LINES_TOTAL_TVAS = sum(EST_LINES_TVAS)

DISCOUNT_TOTAL_HT = sum([d['amount']for d in DISCOUNTS])
DISCOUNT_TVAS = (392,)
DISCOUNT_TOTAL_TVAS = sum(DISCOUNT_TVAS)

HT_TOTAL =  int(LINES_TOTAL_HT - DISCOUNT_TOTAL_HT)
TVA = int(LINES_TOTAL_TVAS - DISCOUNT_TOTAL_TVAS)

# EST_TOTAL = lines + tva + expenses rounded
EST_TOTAL = HT_TOTAL + TVA + ESTIMATION['expenses']
EST_DEPOSIT_HT = int(HT_TOTAL * ESTIMATION['deposit'] / 100.0)
EST_DEPOSIT = int(EST_TOTAL * ESTIMATION['deposit'] / 100.0)
PAYMENTSSUM = sum([p['amount'] for p in PAYMENT_LINES[:-1]])

EST_SOLD = EST_TOTAL - EST_DEPOSIT - PAYMENTSSUM

print "EST_DEPOSIT_HT : %s" % EST_DEPOSIT_HT
print "PAYMENTSSUM : %s" % PAYMENTSSUM
print "EST_DEPOSIT : %s" % EST_DEPOSIT
print "EST_TOTAL : %s" % EST_TOTAL

print "EST_SOLD %s" % EST_SOLD

def get_client():
    client = MagicMock(**CLIENT)
    return client

def get_project():
    project = MagicMock(**PROJECT)
    project.client = get_client()
    project.get_next_estimation_number = lambda :2
    project.get_next_invoice_number = lambda :2
    project.get_next_cancelinvoice_number = lambda :2
    return project

def get_user(datas=USER):
    user = User(**datas)
    return user

def get_task(factory):
    user = get_user()
    task = factory(**TASK)
    task.statusPersonAccount = user
    task.owner = user
    return task

def get_estimation(user=None, project=None):
    est = Estimation(**ESTIMATION)
    for line in LINES:
        l = EstimationLine(**line)
        est.lines.append(l)
    for line in DISCOUNTS:
        l = DiscountLine(**line)
        est.discounts.append(l)
    for line in PAYMENT_LINES:
        l = PaymentLine(**line)
        est.payment_lines.append(l)
    if user is None:
        user = get_user()
    if project is None:
        project = get_project()
    est.project = project
    est.statusPersonAccount = user
    return est

def get_invoice(user=None, project=None, stripped=False):
    inv = Invoice(**INVOICE)
    for line in LINES:
        l = InvoiceLine(**line)
        inv.lines.append(l)
    for line in DISCOUNTS:
        l = DiscountLine(**line)
        inv.discounts.append(l)
    if not stripped:
        if not user:
            user = get_user()
        if not project:
            project = get_project()
        inv.project = project
        inv.statusPersonAccount = user
        inv.owner = user
    return inv

def get_cancelinvoice():
    cinv = CancelInvoice(**CANCELINVOICE)
    for line in LINES:
        l = CancelInvoiceLine(**line)
        cinv.lines.append(l)
    return cinv

class TestTaskModels(BaseTestCase):
    def test_interfaces(self):
        self.assertTrue(verifyObject(ITask, Task()))
        self.assertTrue(verifyObject(IValidatedTask, Estimation()))
        self.assertTrue(verifyObject(IPaidTask, Invoice()))
        self.assertTrue(verifyObject(IPaidTask, CancelInvoice()))
        self.assertTrue(verifyObject(IInvoice, Invoice()))
        self.assertTrue(verifyObject(IInvoice, CancelInvoice()))
        self.assertTrue(verifyObject(IInvoice, ManualInvoice()))

    def test_task_status(self):
        task = get_task(factory=Task)
        #Estimations
        task = get_task(factory=Estimation)
        self.assertTrue(task.is_draft())
        self.assertTrue(task.is_editable())
        self.assertFalse(task.is_valid())
        self.assertFalse(task.has_been_validated())
        self.assertFalse(task.is_waiting())
        task.CAEStatus = "wait"
        self.assertTrue(task.is_waiting())
        self.assertFalse(task.is_valid())
        self.assertFalse(task.is_editable())
        self.assertTrue(task.is_editable(manage=True))
        for i in ("valid", "geninv"):
            task.CAEStatus = i
            self.assertTrue(task.has_been_validated())
            self.assertFalse(task.is_editable())
        # Invoices
        task = get_task(factory=Invoice)
        self.assertTrue(task.is_draft())
        self.assertTrue(task.is_editable())
        self.assertFalse(task.is_valid())
        self.assertFalse(task.has_been_validated())
        self.assertFalse(task.is_waiting())
        task.CAEStatus = "wait"
        self.assertTrue(task.is_waiting())
        self.assertFalse(task.is_valid())
        self.assertFalse(task.is_editable())
        self.assertTrue(task.is_editable(manage=True))
        for i in ("valid", ):
            task.CAEStatus = i
            self.assertTrue(task.has_been_validated())
            self.assertFalse(task.is_editable())
        task.CAEStatus = "paid"
        self.assertTrue(task.is_paid())
        # CancelInvoice
        task = get_task(factory=CancelInvoice)
        self.assertTrue(task.is_draft())
        self.assertTrue(task.is_editable())
        self.assertFalse(task.is_valid())
        self.assertFalse(task.has_been_validated())
        self.assertFalse(task.is_waiting())
        task.CAEStatus = "wait"
        self.assertTrue(task.is_waiting())
        self.assertFalse(task.is_valid())
        self.assertFalse(task.is_editable())
        self.assertTrue(task.is_editable(manage=True))
        task.CAEStatus = "valid"
        self.assertTrue(task.is_valid())
        self.assertFalse(task.is_editable())

    def test_status_change(self):
        # Estimation
        task = get_task(factory=Estimation)
        for st in ("valid", "geninv", "aboest", "invalid"):
            self.assertRaises(Forbidden, task.validate_status, "nutt", st)
        self.assertEqual(task.validate_status("nutt", "wait"), "wait")
        task.CAEStatus = "wait"
        for st in ("draft", "geninv", ):
            self.assertRaises(Forbidden, task.validate_status, "nutt", st)
        self.assertEqual(task.validate_status("nutt", "invalid"), "invalid")
        self.assertEqual(task.validate_status("nutt", "valid"), "valid")
        task.CAEStatus = "valid"
        for st in ("draft", "invalid", ):
            self.assertRaises(Forbidden, task.validate_status, "nutt", st)
        for st in ("geninv", "aboest"):
            self.assertEqual(task.validate_status("nutt", st), st)
        task.CAEStatus = "geninv"
        for st in ("draft", "invalid", "valid", "aboest"):
            self.assertRaises(Forbidden, task.validate_status, "nutt", st)

        # Invoice
        task = get_task(factory=Invoice)
        for st in ("valid", "aboinv", "invalid"):
            self.assertRaises(Forbidden, task.validate_status, "nutt", st)
        self.assertEqual(task.validate_status("nutt", "wait"), "wait")
        task.CAEStatus = "wait"
        for st in ("draft", ):
            self.assertRaises(Forbidden, task.validate_status, "nutt", st)
        self.assertEqual(task.validate_status("nutt", "invalid"), "invalid")
        self.assertEqual(task.validate_status("nutt", "valid"), "valid")
        task.CAEStatus = "valid"
        for st in ("draft", "invalid"):
            self.assertRaises(Forbidden, task.validate_status, "nutt", st)
        for st in ("aboinv", "paid"):
            self.assertEqual(task.validate_status("nutt", st), st)
        task.CAEStatus = "paid"
        for st in ("draft", "invalid", "valid", "aboinv", ):
            self.assertRaises(Forbidden, task.validate_status, "nutt", st)

        # CancelInvoice
        task = get_task(factory=CancelInvoice)
        # Removing Direct validation of the cancelinvoice
        task.CAEStatus = 'wait'
        task.CAEStatus = "valid"
        for st in ("draft",):
            self.assertRaises(Forbidden, task.validate_status, "nutt", st)

class TestComputing(BaseTestCase):
    def test_line_total_ht(self):
        for index, line in enumerate(LINES):
            for obj in InvoiceLine, CancelInvoiceLine, EstimationLine:
                line_obj = obj(**line)
                self.assertEqual(line_obj.total_ht(), EST_LINES_TOTAL_HT[index])
                self.assertEqual(line_obj.total(), EST_LINES_TOTAL_HT[index] +\
                        EST_LINES_TVAS[index])

    def test_lines_total_ht(self):
        task = TaskCompute()
        task.lines = []
        task.discounts = []
        for index, line in enumerate(LINES):
            task.lines.append(InvoiceLine(**line))
        self.assertEqual(task.lines_total_ht(), sum(EST_LINES_TOTAL_HT))
        for obj, line_obj in ((Invoice, InvoiceLine), \
                            (CancelInvoice, CancelInvoiceLine), \
                            (Estimation, EstimationLine)):
            task = get_task(factory=obj)
            for line in LINES:
                task.lines.append(line_obj(**line))
            self.assertEqual(task.lines_total_ht(), sum(EST_LINES_TOTAL_HT))
            for discount in DISCOUNTS:
                task.discounts.append(DiscountLine(**discount))
            self.assertEqual(task.discount_total_ht(), DISCOUNT_TOTAL_HT)

    def test_discount_total_ht(self):
        for i, line in enumerate( DISCOUNTS ):
            line_obj = DiscountLine(**line)
            self.assertEqual(line_obj.total_ht(), DISCOUNTS[i]['amount'])
            self.assertEqual(line_obj.total(), DISCOUNTS[i]['amount'] \
                                                    + DISCOUNT_TVAS[i])

    def test_total_ht(self):
        est = get_estimation()
        self.assertEqual(est.total_ht(),
                    HT_TOTAL)

    def test_tva_amount(self):
        task = TaskCompute()
        line = InvoiceLine(cost=5010, quantity=1, tva=1960)
        task.lines = [line]
        task.discounts = []
        # cf #501
        # ici 5010 correpond à 50€10
        self.assertEqual(task.tva_amount(), 981)

        est = get_estimation()
        self.assertEqual(est.tva_amount(), TVA)

    def test_get_tvas(self):
        task = TaskCompute()
        task.lines = [InvoiceLine(cost=35000, quantity=1, tva=1960),
                      InvoiceLine(cost=40000, quantity=1, tva=550)]
        task.discounts = [DiscountLine(amount=1200, tva=550),
                        DiscountLine(amount=15000, tva=1960)]
        tvas = task.get_tvas()
        self.assertEqual(tvas.keys(), [1960, 550])
        self.assertEqual(tvas[1960], 3920)
        self.assertEqual(tvas[550], 2134)

    def test_total_ttc(self):
        line = InvoiceLine(cost=1030, quantity=1.25, rowIndex=1,
                            tva=1960, description='')
        # cf ticket #501
        # line total : 12.875
        # tva : 2.5235 -> 2.52
        # A confirmer :l'arrondi ici bas
        # => total : 15.39 (au lieu de 15.395)
        task = TaskCompute()
        task.lines = [line]
        task.discounts = []
        self.assertEqual(task.total_ttc(), 1539)

    def test_total(self):
        est = get_estimation()
        self.assertEqual(est.total(), EST_TOTAL)

class TestEstimation(BaseTestCase):
    def test_get_name(self):
        self.assertEqual(Estimation.get_name(5), u"Devis 5")

    def test_duplicate_estimation(self):
        user = get_user(USER2)
        project = get_project()
        phase = MagicMock(id=16)
        est = get_estimation(user, project)
        newest = est.duplicate(user, project, phase)
        self.assertEqual(newest.CAEStatus, 'draft')
        self.assertEqual(newest.project, project)
        self.assertEqual(newest.statusPersonAccount, user)
        self.assertTrue(newest.number.startswith("PRO1_CLI1_D2_"))
        self.assertTrue(newest.phase, phase)
        self.assertEqual(len(est.lines), len(newest.lines))
        self.assertEqual(len(est.payment_lines), len(newest.payment_lines))
        self.assertEqual(len(est.discounts), len(newest.discounts))

    def test_duplicate_estimation_integration(self):
        """
            Here we test the duplication on a real world case
            specifically, the client is not loaded in the session
            causing the insert statement to be fired during duplication
        """
        user = self.session.query(User).first()
        project = self.session.query(Project).first()
        phase = self.session.query(Phase).first()
        est = get_estimation(user, project)
        est.phase = phase
        self.assertEqual(est.statusPersonAccount, user)
        self.assertEqual(est.project, project)
        est.owner_id = user.id
        est = self.session.merge(est)
        self.session.flush()
        newest = est.duplicate(user, project, phase)
        self.session.merge(newest)
        self.session.flush()
        self.assertEqual(newest.phase, phase)

    def test_estimation_deposit(self):
        est = get_estimation()
        self.assertEqual(est.deposit_amount(), EST_DEPOSIT_HT)

    def test_sold(self):
        est = get_estimation()
        self.assertEqual(est.sold(), EST_SOLD)

    def test_payments_sum(self):
        est = get_estimation()
        self.assertEqual(est.sold() + est.deposit_amount_ttc()
                + sum([p.amount for p in est.payment_lines[:-1]]),
                est.total())

    def test_get_number(self):
        project = get_project()
        seq_number = 15
        date = datetime.date(1969, 07, 31)
        self.assertEqual(Estimation.get_number(project, seq_number, date),
                        u"PRO1_CLI1_D15_0769")

    def test_gen_invoice(self):
        est = get_estimation()
        invoices = est.gen_invoices(1)
        for inv in invoices:
            self.session.add(inv)
            self.session.flush()
        invoices = Invoice.query().filter(Invoice.estimation_id==est.id).all()
        #deposit :
        deposit = invoices[0]
        self.assertEqual(deposit.taskDate, datetime.date.today())
        self.assertEqual(deposit.total_ht(), est.deposit_amount())
        self.assertEqual(deposit.lines[0].tva, 1960)
        #intermediate invoices:
        intermediate_invoices = invoices[1:-1]
        for index, line in enumerate(PAYMENT_LINES[:-1]):
            inv = intermediate_invoices[index]
            # ce test échouera jusqu'à ce qu'on ait trouvé une solution
            # alternative à la configuration des acomptes
            self.assertEqual(inv.total(), line['amount'])
            self.assertEqual(inv.taskDate, line['paymentDate'])
            self.assertEqual(inv.lines[0].tva, 1960)
        total = sum([inv.total() for inv in invoices])
        self.assertEqual(total, est.total())

class TestInvoice(BaseViewTest):
    def test_get_name(self):
        self.assertEqual(Invoice.get_name(5), u"Facture 5")
        self.assertEqual(Invoice.get_name(5, sold=True), u"Facture de solde")
        self.assertEqual(Invoice.get_name(5, account=True),
                                                      u"Facture d'acompte 5")

    def test_get_number(self):
        project = get_project()
        seq_number = 15
        date = datetime.date(1969, 07, 31)
        self.assertEqual(Invoice.get_number(project, seq_number, date),
                        u"PRO1_CLI1_F15_0769")
        self.assertEqual(Invoice.get_number(project, seq_number, date,
                        deposit=True), u"PRO1_CLI1_FA15_0769")

#    def test_gen_cancelinvoice(self):
#        user = User(**USER)
#        self.session.add(user)
#        inv = get_invoice(user=user)
#        self.session.add(inv)
#        cinv = inv.gen_cancelinvoice(user.id)
#        self.session.add(cinv)
#        self.session.flush()
#
#        self.assertEqual(cinv.name, "Avoir 2")
#        self.assertEqual(cinv.total_ht(), -1 * inv.total_ht())
#        today = datetime.date.today()
#        self.assertEqual(cinv.taskDate, today)

    def test_gen_cancelinvoice_payment(self):
        user = User(**USER)
        inv = get_invoice(user=user)
        inv.payments.append(Payment(**PAYMENTS[0]))
        cinv = inv.gen_cancelinvoice(user.id)
        self.assertEqual(len(cinv.lines), 5)
        self.assertEqual(cinv.lines[-1].cost, PAYMENTS[0]['amount'])

    def test_duplicate_invoice(self):
        user = get_user(USER2)
        project = get_project()
        phase = MagicMock(id=16)
        inv = get_invoice(user=user, project=project)
        newinv = inv.duplicate(user, project, phase)
        self.assertEqual(len(inv.lines), len(newinv.lines))
        self.assertEqual(len(inv.discounts), len(newinv.discounts))
        self.assertEqual(inv.project, newinv.project)
        self.assertEqual(newinv.statusPersonAccount, user)
        self.assertEqual(newinv.phase, phase)

    def test_duplicate_invoice_integration(self):
        user = self.session.query(User).first()
        project = self.session.query(Project).first()
        phase = self.session.query(Phase).first()
        inv = get_invoice(user, project)
        inv.phase = phase
        inv.owner_id = user.id
        inv = self.session.merge(inv)
        self.session.flush()
        newest = inv.duplicate(user, project, phase)
        self.session.merge(newest)
        self.session.flush()
        self.assertEqual(newest.phase_id, phase.id)
        self.assertEqual(newest.owner_id, user.id)
        self.assertEqual(newest.statusPerson, user.id)
        self.assertEqual(newest.project_id, project.id)


    def test_valid_invoice(self):
        inv = get_invoice(stripped=True)
        self.session.add(inv)
        self.session.flush()
        self.config.testing_securitypolicy(userid='test', permissive=True)
        request = testing.DummyRequest()
        inv.set_status('wait', request, 1)
        self.session.merge(inv)
        self.session.flush()
        inv.set_status('valid', request, 1)
        today = datetime.date.today()
        self.assertEqual(inv.taskDate, today)
        self.assertEqual(inv.officialNumber, 1)

    def test_valid_payment(self):
        inv = get_invoice(stripped=True)
        self.session.add(inv)
        self.session.flush()
        self.config.testing_securitypolicy(userid='test', permissive=True)
        request = testing.DummyRequest()
        inv.set_status('wait', request, 1)
        self.session.merge(inv)
        self.session.flush()
        inv.set_status('valid', request, 1)
        self.session.merge(inv)
        self.session.flush()
        inv.set_status("paid", request, 1, amount=150, mode="CHEQUE")
        inv = self.session.merge(inv)
        self.session.flush()
        invoice = self.session.query(Invoice)\
                .filter(Invoice.id==inv.id).first()
        self.assertEqual(invoice.CAEStatus, 'paid')
        self.assertEqual(len(invoice.payments), 1)
        self.assertEqual(invoice.payments[0].amount, 150)

class TestCancelInvoice(BaseTestCase):
    def test_get_name(self):
        self.assertEqual(CancelInvoice.get_name(5), u"Avoir 5")

    def test_get_number(self):
        project = get_project()
        seq_number = 15
        date = datetime.date(1969, 07, 31)
        self.assertEqual(CancelInvoice.get_number(project, seq_number, date),
                        u"PRO1_CLI1_A15_0769")

class TestManualInvoice(BaseTestCase):
    def test_tva_amount(self):
        m = ManualInvoice(montant_ht=1950)
        self.assertEqual(m.tva_amount(), 0)

class TestEstimationLine(BaseTestCase):
    def test_duplicate_line(self):
        line = EstimationLine(**LINES[1])
        dline = line.duplicate()
        for i in ('rowIndex', 'cost', 'tva', "description", "quantity", "unity"):
            self.assertEqual(getattr(dline, i), getattr(line, i))

    def test_gen_invoiceline(self):
        line = EstimationLine(**LINES[1])
        iline = line.gen_invoice_line()
        for i in ('rowIndex', 'cost', 'tva', "description", "quantity", "unity"):
            self.assertEqual(getattr(line, i), getattr(iline, i))

    def test_total(self):
        i = EstimationLine(cost=1.25, quantity=1.25, tva=1960)
        self.assertEqual(i.total_ht(), 1.5625)
        self.assertEqual(i.total(), 1.86875)

class TestInvoiceLine(BaseTestCase):
    def test_duplicate_line(self):
        line = InvoiceLine(**LINES[1])
        dline = line.duplicate()
        for i in ('rowIndex', 'cost', 'tva', "description", "quantity", "unity"):
            self.assertEqual(getattr(dline, i), getattr(line, i))


    def test_gen_cancelinvoice_line(self):
        line = InvoiceLine(**LINES[1])
        cline = line.gen_cancelinvoice_line()
        for i in ('rowIndex', "description", 'tva', "quantity", "unity"):
            self.assertEqual(getattr(cline, i), getattr(line, i))
        self.assertEqual(cline.cost, -1 * line.cost)

    def test_total(self):
        i = InvoiceLine(cost=1.25, quantity=1.25, tva=1960)
        self.assertEqual(i.total_ht(), 1.5625)
        self.assertEqual(i.total(), 1.86875)

class TestCancelInvoiceLine(BaseTestCase):
    def test_duplicate_line(self):
        line = CancelInvoiceLine(**LINES[1])
        dline = line.duplicate()
        for i in ('rowIndex', 'cost', 'tva', "description", "quantity", "unity"):
            self.assertEqual(getattr(dline, i), getattr(line, i))

    def test_total(self):
        i = CancelInvoiceLine(cost=1.25, quantity=1.25, tva=1960)
        self.assertEqual(i.total_ht(), 1.5625)
        self.assertEqual(i.total(), 1.86875)

class TestPaymentLine(BaseTestCase):
    def test_duplicate(self):
        line = PaymentLine(**PAYMENT_LINES[0])
        dline = line.duplicate()
        for i in ('rowIndex', 'description', 'amount'):
            self.assertEqual(getattr(line, i), getattr(dline, i))
        today = datetime.date.today()
        self.assertEqual(dline.paymentDate, today)

class TestPayment(BaseTestCase):

    def get_task(self):
        task = get_invoice(stripped=True)
        for i in PAYMENTS:
            task.payments.append(Payment(**i))
        return task

    def test_record_payment(self):
        task = self.get_task()
        request_params = {'amount':1500, 'mode':'cheque'}
        record_payment(task, **request_params)
        self.assertEqual(len(task.payments), 3)
        self.assertEqual(task.payments[2].amount, 1500)
        self.session.add(task)
        self.session.flush()

    def test_payment_get_amount(self):
        payment = Payment(**PAYMENTS[1])
        self.assertEqual(payment.get_amount(), 1895)

    def test_invoice_topay(self):
        task = self.get_task()
        self.assertEqual(task.paid(), 3395)
        self.assertEqual(task.topay(), EST_TOTAL - 3395)

    def test_resulted_manual(self):
        task = self.get_task()
        task.CAEStatus = 'wait'
        task.CAEStatus = 'valid'
        task.CAEStatus = 'paid'
        request_params = {'amount':0, 'mode':'cheque', 'resulted':True}
        record_payment(task, **request_params)
        self.assertEqual(task.CAEStatus, 'resulted')

    def test_resulted_auto(self):
        task = self.get_task()
        task.CAEStatus = 'wait'
        task.CAEStatus = 'valid'
        task.CAEStatus = 'paid'
        request_params = {'amount':int(task.topay()), 'mode':'cheque'}
        record_payment(task, **request_params)
        self.assertEqual(task.CAEStatus, 'resulted')

class TestPolymorphic(BaseTestCase):
    def test_invoice(self):
        inv = get_invoice(stripped=True)
        inv.phase_id = 16
        self.session.add(inv)
        self.session.flush()
        task = self.session.query(Task).filter(Task.phase_id==16).first()
        self.assertTrue(isinstance(task, Invoice))

    def test_payment(self):
        invoice = get_invoice(stripped=True)
        invoice.phase_id = 17
        invoice.record_payment(**PAYMENTS[0])
        self.session.add(invoice)
        self.session.flush()
        p1 = self.session.query(Payment).join(Task).filter(Task.phase_id==17).first()
        self.assertTrue(isinstance(p1.task, Invoice))
        self.assertFalse(isinstance(p1.task, CancelInvoice))
