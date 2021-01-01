
"""
Fab QuickStart 0.1.2

Current Working Directory: /Users/val/python/vsc/logic-nw/basic_web_app

From: /Users/val/python/vsc/logic-explore/venv/bin/fab-quick-start

Using Python: 3.8.3 (default, Jul  1 2020, 19:29:47)
[Clang 11.0.3 (clang-1103.0.32.62)]

Favorites: ['name', 'description']

Non Favorites: ['id']

At: 2020-08-19 13:53:32.327988

"""
from flask import flash
from flask_appbuilder import ModelView
from flask_appbuilder.models.sqla.interface import SQLAInterface, log
from . import appbuilder, db
from .models import *




class CategoryModelView(ModelView):
   datamodel = SQLAInterface(Category)
   list_columns = ["CategoryName", "Description"]
   show_columns = ["CategoryName", "Description", "Id"]
   edit_columns = ["CategoryName", "Description", "Id"]
   add_columns = ["CategoryName", "Description", "Id"]
   related_views = []

appbuilder.add_view(
      CategoryModelView, "Category List", icon="fa-folder-open-o", category="Menu")


class OrderDetailModelView(ModelView):
   datamodel = SQLAInterface(OrderDetail)
   list_columns = [
"Id", "ProductOrdered.ProductName", "UnitPrice", "Quantity", "Amount"]
   show_columns = [
"Id", "ProductOrdered.ProductName", "OrderHeader.ShipName", "UnitPrice", "Quantity", "Discount", "Amount", "OrderId", "ProductId"]
   edit_columns = [
"Id", "UnitPrice", "Quantity", "OrderId", "ProductId"]
   add_columns = [
"Id", "UnitPrice", "Quantity", "OrderId", "ProductId"]
   related_views = []

appbuilder.add_view(
      OrderDetailModelView, "OrderDetail List", icon="fa-folder-open-o", category="Menu")





class OrderModelView(ModelView):
   datamodel = SQLAInterface(Order)
   list_columns = ["Id", "ShipName", "AmountTotal", "OrderDate", "ShippedDate"]
   show_columns = ["ShipName", "Customer.CompanyName", "OrderDate", "RequiredDate", "ShippedDate", "ShipVia", "Freight", "ShipAddress", "ShipCity", "ShipRegion", "ShipPostalCode", "ShipCountry", "AmountTotal", "EmployeeId", "Id", "CustomerId"]
   edit_columns = ["ShipName", "OrderDate", "RequiredDate", "ShippedDate", "ShipVia", "Freight", "ShipAddress", "ShipCity", "ShipRegion", "ShipPostalCode", "ShipCountry", "EmployeeId", "Id", "CustomerId"]
   add_columns = ["ShipName", "OrderDate", "RequiredDate", "ShippedDate", "ShipVia", "Freight", "ShipAddress", "ShipCity", "ShipRegion", "ShipPostalCode", "ShipCountry", "EmployeeId", "Id", "CustomerId"]
   related_views = [OrderDetailModelView]

appbuilder.add_view(
      OrderModelView, "Order List", icon="fa-folder-open-o", category="Menu")





class CustomerModelView(ModelView):
   datamodel = SQLAInterface(Customer)
   list_columns = ["Id", "CompanyName", "ContactName", "Balance", "CreditLimit", "OrderCount", "UnpaidOrderCount"]
   show_columns = ["CompanyName",  "Balance", "CreditLimit", "OrderCount", "UnpaidOrderCount", "ContactName", "ContactTitle", "Address", "City", "Region", "PostalCode", "Country", "Phone", "Fax", "Id"]
   edit_columns = ["CompanyName",  "CreditLimit",  "OrderCount", "UnpaidOrderCount", "ContactName", "ContactTitle", "Address", "City", "Region", "PostalCode", "Country", "Phone", "Fax", "Id"]
   add_columns = ["CompanyName",   "CreditLimit",  "OrderCount", "UnpaidOrderCount", "ContactName", "ContactTitle", "Address", "City", "Region", "PostalCode", "Country", "Phone", "Fax", "Id"]
   related_views = [OrderModelView]

appbuilder.add_view(
      CustomerModelView, "Customer List", icon="fa-folder-open-o", category="Menu")

""" for debug
class MyFormView(CustomerModelView):
   # form = MyForm
   form_title = 'This is my first form view'
   message = 'My form submitted'

   def form_get(self, form):
      form.field1.data = 'This was prefilled'
      log.fatal("hoo haa")
      # raise Exception("my exception")

   def form_post(self, form):
      # post process form
      log.fatal("haa hoo")
      flash(self.message, 'info')
      # raise Exception("my exception")


appbuilder.add_view(MyFormView, "My form View", icon="fa-group", label='My form View Label',
                    category="My Forms", category_icon="fa-cogs")

"""

class CustomerDemographicModelView(ModelView):
   datamodel = SQLAInterface(CustomerDemographic)
   list_columns = ["Id", "CustomerDesc"]
   show_columns = ["Id", "CustomerDesc"]
   edit_columns = ["Id", "CustomerDesc"]
   add_columns = ["Id", "CustomerDesc"]
   related_views = []

appbuilder.add_view(
      CustomerDemographicModelView, "CustomerDemographic List", icon="fa-folder-open-o", category="Menu")





class EmployeeTerritoryModelView(ModelView):
   datamodel = SQLAInterface(EmployeeTerritory)
   list_columns = ["Id", "Employee.LastName", "Territory.TerritoryDescription"]
   show_columns = ["Id", "Employee.LastName", "Territory.TerritoryDescription", "EmployeeId", "TerritoryId"]
   edit_columns = ["Id", "EmployeeId", "TerritoryId"]
   add_columns = ["Id", "EmployeeId", "TerritoryId"]
   related_views = []

appbuilder.add_view(
      EmployeeTerritoryModelView, "EmployeeTerritory List", icon="fa-folder-open-o", category="Menu")





class EmployeeModelView(ModelView):
   datamodel = SQLAInterface(Employee)
   list_columns = ["LastName", "FirstName", "Title", "TitleOfCourtesy", "BirthDate"]
   show_columns = ["LastName", "FirstName", "Title", "TitleOfCourtesy", "BirthDate", "HireDate", "Address", "City", "Region", "PostalCode", "Country", "HomePhone", "Extension", "Photo", "Notes", "ReportsTo", "PhotoPath", "Id"]
   edit_columns = ["LastName", "FirstName", "Title", "TitleOfCourtesy", "BirthDate", "HireDate", "Address", "City", "Region", "PostalCode", "Country", "HomePhone", "Extension", "Photo", "Notes", "ReportsTo", "PhotoPath", "Id"]
   add_columns = ["LastName", "FirstName", "Title", "TitleOfCourtesy", "BirthDate", "HireDate", "Address", "City", "Region", "PostalCode", "Country", "HomePhone", "Extension", "Photo", "Notes", "ReportsTo", "PhotoPath", "Id"]
   related_views = [OrderModelView, EmployeeTerritoryModelView]

appbuilder.add_view(
      EmployeeModelView, "Employee List", icon="fa-folder-open-o", category="Menu")


# table already generated per recursion: OrderDetail


class ProductModelView(ModelView):
   datamodel = SQLAInterface(Product)
   list_columns = ["ProductName", "QuantityPerUnit", "UnitPrice", "UnitsInStock", "UnitsOnOrder"]
   show_columns = ["ProductName", "QuantityPerUnit", "UnitPrice", "UnitsInStock", "UnitsOnOrder", "ReorderLevel", "Discontinued", "Id", "CategoryId", "SupplierId"]
   edit_columns = ["ProductName", "QuantityPerUnit", "UnitPrice", "UnitsInStock", "UnitsOnOrder", "ReorderLevel", "Discontinued", "Id", "CategoryId", "SupplierId"]
   add_columns = ["ProductName", "QuantityPerUnit", "UnitPrice", "UnitsInStock", "UnitsOnOrder", "ReorderLevel", "Discontinued", "Id", "CategoryId", "SupplierId"]
   related_views = [OrderDetailModelView]

appbuilder.add_view(
      ProductModelView, "Product List", icon="fa-folder-open-o", category="Menu")





class RegionModelView(ModelView):
   datamodel = SQLAInterface(Region)
   list_columns = ["RegionDescription"]
   show_columns = ["RegionDescription", "Id"]
   edit_columns = ["RegionDescription", "Id"]
   add_columns = ["RegionDescription", "Id"]
   related_views = []

appbuilder.add_view(
      RegionModelView, "Region List", icon="fa-folder-open-o", category="Menu")





class ShipperModelView(ModelView):
   datamodel = SQLAInterface(Shipper)
   list_columns = ["CompanyName", "Phone"]
   show_columns = ["CompanyName", "Phone", "Id"]
   edit_columns = ["CompanyName", "Phone", "Id"]
   add_columns = ["CompanyName", "Phone", "Id"]
   related_views = []

appbuilder.add_view(
      ShipperModelView, "Shipper List", icon="fa-folder-open-o", category="Menu")





class SupplierModelView(ModelView):
   datamodel = SQLAInterface(Supplier)
   list_columns = ["CompanyName", "ContactName", "ContactTitle", "Address", "City"]
   show_columns = ["CompanyName", "ContactName", "ContactTitle", "Address", "City", "Region", "PostalCode", "Country", "Phone", "Fax", "HomePage", "Id"]
   edit_columns = ["CompanyName", "ContactName", "ContactTitle", "Address", "City", "Region", "PostalCode", "Country", "Phone", "Fax", "HomePage", "Id"]
   add_columns = ["CompanyName", "ContactName", "ContactTitle", "Address", "City", "Region", "PostalCode", "Country", "Phone", "Fax", "HomePage", "Id"]
   related_views = []

appbuilder.add_view(
      SupplierModelView, "Supplier List", icon="fa-folder-open-o", category="Menu")


# table already generated per recursion: EmployeeTerritory


class TerritoryModelView(ModelView):
   datamodel = SQLAInterface(Territory)
   list_columns = ["TerritoryDescription"]
   show_columns = ["TerritoryDescription", "Id", "RegionId"]
   edit_columns = ["TerritoryDescription", "Id", "RegionId"]
   add_columns = ["TerritoryDescription", "Id", "RegionId"]
   related_views = [EmployeeTerritoryModelView]

appbuilder.add_view(
      TerritoryModelView, "Territory List", icon="fa-folder-open-o", category="Menu")


# skip admin table: ab_permission
# skip admin table: ab_register_user
# skip admin table: ab_role
# skip admin table: ab_user
# skip admin table: ab_view_menu
# table already generated per recursion: CustomerCustomerDemo# table already generated per recursion: EmployeeTerritory# table already generated per recursion: Order# skip admin table: ab_permission_view
# skip admin table: ab_user_role
# table already generated per recursion: OrderDetail# skip admin table: ab_permission_view_role
#  21 table(s) in model; generated 13 page(s), including 5 related_view(s).
