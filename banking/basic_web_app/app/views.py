
"""
Fab QuickStart 0.1.2

Current Working Directory: /Users/val/python/pycharm/Logic-Bank/banking_app

From: /Users/val/python/pycharm/Logic-Bank/venv/bin/fab-quick-start

Using Python: 3.8.3 (default, Aug  5 2020, 16:59:52) 
[Clang 11.0.3 (clang-1103.0.32.62)]

Favorites: ['name', 'description']

Non Favorites: ['id']

At: 2020-09-30 08:07:52.451524

"""

from flask_appbuilder import ModelView
from flask_appbuilder.models.sqla.interface import SQLAInterface
from . import appbuilder, db
from .models import *




class ValidAcctTypeModelView(ModelView):
   datamodel = SQLAInterface(ValidAcctType)
   list_columns = ["AcctDescription", "AcctType"]
   show_columns = ["AcctDescription", "AcctType"]
   edit_columns = ["AcctDescription", "AcctType"]
   add_columns = ["AcctDescription", "AcctType"]
   related_views = []

appbuilder.add_view(
      ValidAcctTypeModelView, "ValidAcctType List", icon="fa-folder-open-o", category="Menu")





class ValidCreditModelView(ModelView):
   datamodel = SQLAInterface(ValidCredit)
   list_columns = ["creditCode", "displayValue", "MaxCreditLimit"]
   show_columns = ["creditCode", "displayValue", "MaxCreditLimit"]
   edit_columns = ["creditCode", "displayValue", "MaxCreditLimit"]
   add_columns = ["creditCode", "displayValue", "MaxCreditLimit"]
   related_views = []

appbuilder.add_view(
      ValidCreditModelView, "ValidCredit List", icon="fa-folder-open-o", category="Menu")





class ValidStateModelView(ModelView):
   datamodel = SQLAInterface(ValidState)
   list_columns = ["stateName", "stateCode"]
   show_columns = ["stateName", "stateCode"]
   edit_columns = ["stateName", "stateCode"]
   add_columns = ["stateName", "stateCode"]
   related_views = []

appbuilder.add_view(
      ValidStateModelView, "ValidState List", icon="fa-folder-open-o", category="Menu")





class TRANSFERFUNDModelView(ModelView):
   datamodel = SQLAInterface(TRANSFERFUND)
   list_columns = ["TransId", "CUSTOMER.Name", "FromAcct", "FromCustNum", "ToAcct"]
   show_columns = ["TransId", "CUSTOMER.Name", "FromAcct", "FromCustNum", "ToAcct", "ToCustNum", "TransferAmt", "TransDate"]
   edit_columns = ["TransId", "FromAcct", "FromCustNum", "ToAcct", "ToCustNum", "TransferAmt", "TransDate"]
   add_columns = ["TransId", "FromAcct", "FromCustNum", "ToAcct", "ToCustNum", "TransferAmt", "TransDate"]
   related_views = []

appbuilder.add_view(
      TRANSFERFUNDModelView, "TRANSFERFUND List", icon="fa-folder-open-o", category="Menu")






# table already generated per recursion: TRANSFERFUND


class ALERTModelView(ModelView):
   datamodel = SQLAInterface(ALERT)
   list_columns = ["AlertID", "CUSTOMER.Name", "CustNum", "AcctNum", "WhenBalance"]
   show_columns = ["AlertID", "CUSTOMER.Name", "CustNum", "AcctNum", "WhenBalance", "AccountBalance", "EmailAddress"]
   edit_columns = ["AlertID", "CustNum", "AcctNum", "WhenBalance", "AccountBalance", "EmailAddress"]
   add_columns = ["AlertID", "CustNum", "AcctNum", "WhenBalance", "AccountBalance", "EmailAddress"]
   related_views = []

appbuilder.add_view(
      ALERTModelView, "ALERT List", icon="fa-folder-open-o", category="Menu")





class CHECKINGTRANSModelView(ModelView):
   datamodel = SQLAInterface(CHECKINGTRANS)
   list_columns = ["TransId", "CHECKING.AcctNum", "AcctNum", "CustNum", "TransDate"]
   show_columns = ["TransId", "CHECKING.AcctNum", "AcctNum", "CustNum", "TransDate", "DepositAmt", "WithdrawlAmt", "Total", "ChkNo", "ImageURL"]
   edit_columns = ["TransId", "AcctNum", "CustNum", "TransDate", "DepositAmt", "WithdrawlAmt", "Total", "ChkNo", "ImageURL"]
   add_columns = ["TransId", "AcctNum", "CustNum", "TransDate", "DepositAmt", "WithdrawlAmt", "Total", "ChkNo", "ImageURL"]
   related_views = []

appbuilder.add_view(
      CHECKINGTRANSModelView, "CHECKINGTRANS List", icon="fa-folder-open-o", category="Menu")


# table already generated per recursion: CHECKINGTRANS


class CHECKINGModelView(ModelView):
   datamodel = SQLAInterface(CHECKING)
   list_columns = ["AcctNum", "CUSTOMER.Name", "CustNum", "Deposits", "Withdrawls"]
   show_columns = ["AcctNum", "CUSTOMER.Name", "CustNum", "Deposits", "Withdrawls", "CurrentBalance", "AvailableBalance", "ItemCount", "CreditCode", "CreditLimit", "AcctType"]
   edit_columns = ["AcctNum", "CustNum", "Deposits", "Withdrawls", "CurrentBalance", "AvailableBalance", "ItemCount", "CreditCode", "CreditLimit", "AcctType"]
   add_columns = ["AcctNum", "CustNum", "Deposits", "Withdrawls", "CurrentBalance", "AvailableBalance", "ItemCount", "CreditCode", "CreditLimit", "AcctType"]
   related_views = [CHECKINGTRANSModelView, CHECKINGTRANSModelView]

appbuilder.add_view(
      CHECKINGModelView, "CHECKING List", icon="fa-folder-open-o", category="Menu")





class LOCTRANSACTIONModelView(ModelView):
   datamodel = SQLAInterface(LOCTRANSACTION)
   list_columns = ["TransId", "LINEOFCREDIT.CustNum", "TransDate", "PaymentAmt", "ChargeAmt"]
   show_columns = ["TransId", "LINEOFCREDIT.CustNum", "TransDate", "PaymentAmt", "ChargeAmt", "ChargeType", "CustNum", "AcctNum"]
   edit_columns = ["TransId", "TransDate", "PaymentAmt", "ChargeAmt", "ChargeType", "CustNum", "AcctNum"]
   add_columns = ["TransId", "TransDate", "PaymentAmt", "ChargeAmt", "ChargeType", "CustNum", "AcctNum"]
   related_views = []

appbuilder.add_view(
      LOCTRANSACTIONModelView, "LOCTRANSACTION List", icon="fa-folder-open-o", category="Menu")


# table already generated per recursion: LOCTRANSACTION

""" val - ??
class LOCTRANSACTIONSModelView(ModelView):
   datamodel = SQLAInterface(LOCTRANSACTIONS)
   list_columns = ["TransId", "LINEOFCREDIT.CustNum", "TransDate", "PaymentAmt", "ChargeAmt"]
   show_columns = ["TransId", "LINEOFCREDIT.CustNum", "TransDate", "PaymentAmt", "ChargeAmt", "ChargeType", "CustNum", "AcctNum"]
   edit_columns = ["TransId", "TransDate", "PaymentAmt", "ChargeAmt", "ChargeType", "CustNum", "AcctNum"]
   add_columns = ["TransId", "TransDate", "PaymentAmt", "ChargeAmt", "ChargeType", "CustNum", "AcctNum"]
   related_views = []

appbuilder.add_view(
      LOCTRANSACTIONSModelView, "LOCTRANSACTIONS List", icon="fa-folder-open-o", category="Menu")

"""
# table already generated per recursion: LOCTRANSACTIONS


class LINEOFCREDITModelView(ModelView):
   datamodel = SQLAInterface(LINEOFCREDIT)
   list_columns = ["CustNum", "CUSTOMER.Name", "AcctNum", "OverdaftFeeAmt", "LineOfCreditAmt"]
   show_columns = ["CustNum", "CUSTOMER.Name", "AcctNum", "OverdaftFeeAmt", "LineOfCreditAmt", "TotalCharges", "TotalPayments", "AvailableBalance", "Id"]
   edit_columns = ["CustNum", "AcctNum", "OverdaftFeeAmt", "LineOfCreditAmt", "TotalCharges", "TotalPayments", "AvailableBalance", "Id"]
   add_columns = ["CustNum", "AcctNum", "OverdaftFeeAmt", "LineOfCreditAmt", "TotalCharges", "TotalPayments", "AvailableBalance", "Id"]
   related_views = [LOCTRANSACTIONModelView]

appbuilder.add_view(
      LINEOFCREDITModelView, "LINEOFCREDIT List", icon="fa-folder-open-o", category="Menu")





class SAVINGSTRANSModelView(ModelView):
   datamodel = SQLAInterface(SAVINGSTRANS)
   list_columns = ["TransId", "SAVING.AcctNum", "AcctNum", "CustNum", "TransDate"]
   show_columns = ["TransId", "SAVING.AcctNum", "AcctNum", "CustNum", "TransDate", "DepositAmt", "WithdrawlAmt", "Total"]
   edit_columns = ["TransId", "AcctNum", "CustNum", "TransDate", "DepositAmt", "WithdrawlAmt", "Total"]
   add_columns = ["TransId", "AcctNum", "CustNum", "TransDate", "DepositAmt", "WithdrawlAmt", "Total"]
   related_views = []

appbuilder.add_view(
      SAVINGSTRANSModelView, "SAVINGSTRANS List", icon="fa-folder-open-o", category="Menu")


# table already generated per recursion: SAVINGSTRANS


class SAVINGModelView(ModelView):
   datamodel = SQLAInterface(SAVING)
   list_columns = ["AcctNum", "CUSTOMER.Name", "CustNum", "Deposits", "Withdrawls"]
   show_columns = ["AcctNum", "CUSTOMER.Name", "CustNum", "Deposits", "Withdrawls", "CurrentBalance", "AvailableBalance", "ItemCount", "AcctType"]
   edit_columns = ["AcctNum", "CustNum", "Deposits", "Withdrawls", "CurrentBalance", "AvailableBalance", "ItemCount", "AcctType"]
   add_columns = ["AcctNum", "CustNum", "Deposits", "Withdrawls", "CurrentBalance", "AvailableBalance", "ItemCount", "AcctType"]
   related_views = [SAVINGSTRANSModelView, SAVINGSTRANSModelView]

appbuilder.add_view(
      SAVINGModelView, "SAVING List", icon="fa-folder-open-o", category="Menu")





class CUSTOMERModelView(ModelView):
   datamodel = SQLAInterface(CUSTOMER)
   list_columns = ["Name", "CustNum", "CheckingAcctBal", "SavingsAcctBal", "TotalBalance"]
   show_columns = ["Name", "CustNum", "CheckingAcctBal", "SavingsAcctBal", "TotalBalance", "Street", "City", "State", "ZIP", "Phone", "emailAddress"]
   edit_columns = ["Name", "CustNum", "CheckingAcctBal", "SavingsAcctBal", "TotalBalance", "Street", "City", "State", "ZIP", "Phone", "emailAddress"]
   add_columns = ["Name", "CustNum", "CheckingAcctBal", "SavingsAcctBal", "TotalBalance", "Street", "City", "State", "ZIP", "Phone", "emailAddress"]
   related_views = [TRANSFERFUNDModelView, TRANSFERFUNDModelView, ALERTModelView, CHECKINGModelView, LINEOFCREDITModelView, SAVINGModelView]

appbuilder.add_view(
      CUSTOMERModelView, "CUSTOMER List", icon="fa-folder-open-o", category="Menu")


# table already generated per recursion: ALERT# table already generated per recursion: CHECKING# table already generated per recursion: LINEOFCREDIT# table already generated per recursion: SAVING# table already generated per recursion: CHECKINGTRANS# table already generated per recursion: LOCTRANSACTION# table already generated per recursion: SAVINGSTRANS# table already generated per recursion: LOCTRANSACTIONS# skip admin table: ab_permission
# skip admin table: ab_permission_view
# skip admin table: ab_view_menu
# skip admin table: ab_permission_view_role
# skip admin table: ab_role
# skip admin table: ab_register_user
# skip admin table: ab_user
# skip admin table: ab_user_role
#  21 table(s) in model; generated 14 page(s), including 4 related_view(s).


