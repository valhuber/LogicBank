from typing import List

import sqlalchemy
from sqlalchemy import inspect, text
from sqlalchemy.orm import base
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import object_mapper, session, relationships, RelationshipProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.functions import Function

from datetime import datetime, date, timezone
from decimal import Decimal

import logic_bank
from logic_bank.rule_bank.rule_bank import RuleBank
from sqlalchemy.ext.declarative import declarative_base

# from logic_bank.exec_row_logic.parent_role_adjuster import ParentRoleAdjuster
from logic_bank.rule_bank import rule_bank_withdraw
from logic_bank.rule_type.constraint import Constraint
from logic_bank.rule_type.derivation import Derivation
from logic_bank.rule_type.formula import Formula
from logic_bank.rule_type.parent_cascade import ParentCascade, ParentCascadeAction
from logic_bank.rule_type.parent_check import ParentCheck
from logic_bank.rule_type.row_event import EarlyRowEvent, RowEvent
from logic_bank.util import ConstraintException, DotDict


class LogicRow:
    """
    Wraps row and  old_row, plus methods for insert, update and delete - rule enforcement

    Passed to user logic, mainly to make updates - with logic, for example

        row = sqlalchemy read

        logic_row.update(row=row, msg="my log message")

    Additional instance variables: ins_upd_dlt, nest_level, session, etc.

    Helper Methods
        are_attributes_changed, set_same_named_attributes,
        get_parent_logic_row(role_name), get_derived_attributes, log, etc

    Called from client, from before_flush listeners, and here for parent/child chaining
    """

    def __init__(self, row: base, old_row: base, ins_upd_dlt: str, nest_level: int,
                 a_session: session, row_sets: object):
        """
        Note adds self to row_sets (if supplied), for later commit-phase logic
        """
        self.session = a_session
        self.row = row  # type(base)
        """ mapped row """
        self.old_row = old_row
        """ old mapped row """
        self.ins_upd_dlt = ins_upd_dlt
        """ values are 'ins', 'upd' or 'dlt' """
        self.ins_upd_dlt_initial = ins_upd_dlt  # order inserted, then adjusted
        self.nest_level = nest_level
        self.reason = "?"  # set by insert, update and delete
        """ if starts with cascade, triggers cascade processing """

        self.row_sets = row_sets
        fixme_set_processed_in_init = False
        if fixme_set_processed_in_init:  # ALS clone order - this makes order look processed (wrongly)
            if row_sets is not None:  # eg, for debug as in upd_order_shipped test
                row_sets.add_processed_logic(logic_row=self)  # used in commit logic

        rb = RuleBank()
        self.rb = rb
        self.session = a_session
        self.some_base = declarative_base()
        self.name = ""
        """ class name """
        self.table_meta = None
        """ class definition """
        self.table_name = ""

        new_way = True
        if new_way:
            self.class_def = type(self.row)
            self.name = type(self.row).__name__  # class name (not table name)
            self.table_meta = None
            self.table_name = "Empty Row - Unknown table_name"
            if self.row is not None:
                self.table_name = self.class_def.__tablename__
                if self.name in row.metadata.tables:  # class Order, table Order
                    self.table_meta = row.metadata.tables[self.name]
                    self.log_engine("Using Class Name: " + self.name)
                else:  # eg, nw OrderClass has table OrderZ ()
                    self.table_meta = row.metadata.tables[self.table_name]
                    self.log_engine("Using Table Name (not Class Name): " + self.table_name)
        else:
            self.name = type(self.row).__name__  # class name (not table name)
            self.table_meta = None
            if self.row is not None:
                if type(self.row).__name__ in row.metadata.tables:
                    self.table_meta = row.metadata.tables[type(self.row).__name__]
                else:
                    self.table_meta = inspect(self.row)
                    self.log_engine("Using Class Name (not Table Name): " + self.name)

    def _get_attr_name(self, mapper, attr) -> str:
        attr_name = None
        """ polymorphism is for wimps - find the name
            returns None if bad name, or is collection, or is object
        """
        if hasattr(attr, "key"):
            attr_name = attr.key
        elif isinstance(attr, hybrid_property):
            attr_name = attr.__name__
        elif hasattr(attr, "__name__"):
            attr_name = attr.__name__
        elif hasattr(attr, "name"):
            attr_name = attr.name
        if attr_name == "Customerxx":
            print("Debug Stop")
        if hasattr(attr, "impl"):
            if attr.impl.collection:
                attr_name = None
            if isinstance(attr.impl, sqlalchemy.orm.attributes.ScalarObjectAttributeImpl):
                attr_name = None
        return attr_name

    def __str__(self):
        result = ".."
        for x in range(self.nest_level):
            result += ".."
        result += self.name + "["  # class, not self.row.__tablename__
        my_meta = self.table_meta
        if not hasattr(my_meta, "primary_key"):
            result += "not available"
        else:  # my_meta.primary_key.columns.keys()
            key_cols = my_meta.primary_key.columns.keys()
            is_first = True
            for each_key_col in key_cols:
                if not is_first:
                    result += " | "
                is_first = False
                value = getattr(self.row, each_key_col)
                if isinstance(value, str):
                    result += value
                else:
                    result += str(value)
        result += "]: "
        cols = self.row.__table__.columns
        sorted_cols = sorted(cols, key=lambda col: col.name)
        is_first = True
        row_mapper = object_mapper(self.row)
        if self.row.__tablename__ == "Customerxx":
            print("Debug Stop here")
        for each_attr in row_mapper.column_attrs:  # avoid parent objects, child collections
            is_hybrid = isinstance(each_attr, hybrid_property)
            each_attr_name = self._get_attr_name(mapper=row_mapper, attr=each_attr)
            if each_attr_name is None:  # parent or child-list
                pass  # don't print, don't even call (avoid sql)
            else:
                if not is_first:
                    result += ", "
                is_first = False
                if each_attr_name == "Idxx":
                    print("Debug Stop here")
                value = getattr(self.row, each_attr_name)
                result += each_attr_name + ": "
                old_value = value
                if self.old_row is not None and \
                        hasattr(self.old_row, each_attr_name):
                    old_value = getattr(self.old_row, each_attr_name)
                if value != old_value:
                    result += ' [' + str(old_value) + '-->] '
                if isinstance(value, str):
                    result += value
                else:
                    result += str(value)
        result += f'  row: {str(hex(id(self.row)))}'
        result += f'  session: {str(hex(id(self.session)))}'
        result += f'  ins_upd_dlt: {(self.ins_upd_dlt)}'
        return result  # str(my_dict)

    def log(self, msg: str) -> str:
        """
        prints to logic_logger: row/old_row, indented, inserting msg
        """
        output = str(self)
        output = output.replace("]:", "] {" + msg + "}", 1)
        logic_bank.logic_logger.info(output)  # more on this later
        return output

    def log_engine(self, msg: str):
        """
        prints to engine_logger: row/old_row, indented, inserting msg
        """
        output = str(self)
        output = output.replace("]:", "] {" + msg + "}", 1)
        logic_bank.engine_logger.debug(output)

    def new_logic_row(self, new_row_class: sqlalchemy.orm.DeclarativeMeta) -> 'LogicRow':
        """ creates a new row of type new_row_class
            applies eager default
        """
        new_row = new_row_class()
        result = LogicRow(row=new_row,
                          old_row=new_row,
                          ins_upd_dlt="ins",
                          nest_level=self.nest_level + 1,
                          a_session=self.session,
                          row_sets=self.row_sets)
        self.session.add(new_row)
        result._eager_defaults()
        return result

    def _make_copy(self, a_row: base) -> base:
        """
        returns DotDict copy of row, or None

        :param a_row:
        :return:
        """

        result = None
        if a_row is not None:
            result = DotDict({})
            row_mapper = object_mapper(a_row)
            for each_attr in row_mapper.column_attrs:  # all_orm_descriptors:
                each_attr_name = self._get_attr_name(mapper=row_mapper, attr=each_attr)
                if each_attr_name is None:  # is parent or collection?
                    debug_stop_prove_parents_and_collections_skipped = True  # iff all_orm_descriptors
                    # print("make_copy NULL attr: " + str(result_class) + "." + str(each_attr))
                else:
                    # print("make_copy attr: " + str(result_class) + "." + each_attr_name)
                    result[each_attr_name] = getattr(a_row, each_attr_name)
        return result

    def _get_parent_logic_row(self, role_name: str, from_row: base = None) -> 'LogicRow':
        """ get parent *and* set parent accessor """
        row = self.row
        if from_row is not None:
            row = from_row
        debug_set_parents_for_inserts = True  # interim, for debug (this failed once, keeping watch)
        parent_row = None
        if hasattr(row, role_name):  # for client updates, old is obj_view, not base
            parent_row = getattr(row, role_name)
        if parent_row is None:
            my_mapper = object_mapper(self.row)
            role_def = my_mapper.relationships.get(role_name)
            if role_def is None:
                raise Exception(f"FIXME invalid role name {role_name}")
            parent_key = {}
            for each_child_col, each_parent_col in role_def.local_remote_pairs:
                parent_key[each_parent_col.name] = getattr(row, each_child_col.name)
            parent_class = role_def.entity.class_
            # https://docs.sqlalchemy.org/en/13/orm/query.html#the-query-object
            parent_row = self.session.query(parent_class).get(parent_key)
            if self.ins_upd_dlt == "upd" or debug_set_parents_for_inserts:  # eg, add order - don't tell sqlalchemy to add cust
                setattr(row, role_name, parent_row)
        old_parent = self._make_copy(parent_row)
        parent_logic_row = LogicRow(row=parent_row, old_row=old_parent, ins_upd_dlt="*", nest_level=1 + self.nest_level,
                                    a_session=self.session, row_sets=self.row_sets)
        return parent_logic_row

    def _early_row_events(self):
        self.log_engine("early_events")
        early_row_events = rule_bank_withdraw.rules_of_class(self, EarlyRowEvent)
        for each_row_event in early_row_events:
            each_row_event.execute(self)

    def _row_events(self):
        self.log_engine("row_events")
        row_events = rule_bank_withdraw.rules_of_class(self, RowEvent)
        for each_row_event in row_events:
            each_row_event.execute(self)

    def _copy_rules(self):
        """ runs copy rules (get parent values on insert, no action on parent update) """
        copy_rules = rule_bank_withdraw.copy_rules(self)
        for role_name, copy_rules_for_table in copy_rules.items():
            logic_row = self
            if logic_row.ins_upd_dlt == "ins" or \
                    logic_row._is_different_parent(parent_role_name=role_name):
                # self.log("copy_rules for role: " + role_name)
                attributes_copied = ""
                parent_logic_row = logic_row._get_parent_logic_row(role_name)
                for each_copy_rule in copy_rules_for_table:  # TODO consider orphans
                    if attributes_copied == "":
                        attributes_copied = each_copy_rule._column
                    else:
                        attributes_copied += f', {each_copy_rule._column}'
                    each_copy_rule.execute(logic_row, parent_logic_row)
                self.log(f'copy_rules for role: {role_name} - {attributes_copied}')

    def is_inserted(self) -> bool:
        """ return True if self.ins_upd_dlt == "ins" else False """
        return True if self.ins_upd_dlt == "ins" else False

    def is_updated(self) -> bool:
        """ return True if self.ins_upd_dlt == "upd" else False """
        return True if self.ins_upd_dlt == "upd" else False

    def is_deleted(self) -> bool:
        """ return True if self.ins_upd_dlt == "dlt" else False """
        return True if self.ins_upd_dlt == "dlt" else False

    def _get_parent_role_def(self, parent_role_name: str):
        """ returns sqlalchemy role_def """
        my_mapper = object_mapper(self.row)
        role_def = my_mapper.relationships.get(parent_role_name)
        if role_def is None:
            raise Exception(f"FIXME invalid role name {parent_role_name}")
        return role_def

    def link(self, to_parent: 'LogicRow', is_copy: bool = False):
        """
        set self.to_parent (parent_accessor) = to_parent

        Example
            if logic_row.are_attributes_changed([Employee.Salary, Employee.Title]):
                copy_to_logic_row = logic_row.new_logic_row(EmployeeAudit)
                copy_to_logic_row.link(to_parent=logic_row)  # link to parent Employee
                copy_to_logic_row.set_same_named_attributes(logic_row)
                copy_to_logic_row.insert(reason="Manual Copy " + copy_to_logic_row.name)  # triggers rules...

        Args:
            to_parent: mapped class that is parent to this logic_row
            is_copy: optional, suppress FK not null (eg, copy_children)

        """
        parent_mapper = object_mapper(to_parent.row)
        parents_relationships = parent_mapper.relationships
        parent_role_name = None
        parent_reln_to_child_db = None
        child = self.row
        for each_relationship in parents_relationships:  # eg, Payment has child PaymentAllocation
            if each_relationship.direction == sqlalchemy.orm.interfaces.ONETOMANY:  # PA
                each_parent_role_name = each_relationship.back_populates  # eg, AllocationList
                child_row_class_name = str(child.__class__.__name__)  # eg, PaymentAllocation
                child_reln_class_name = str(
                    each_relationship.entity.class_.__name__)  # eg., <class 'models.PaymentAllocation'>
                # instance fails - see https://github.com/valhuber/LogicBank/issues/6
                if child_row_class_name == child_reln_class_name:
                    if parent_role_name is not None:
                        raise Exception("TODO - disambiguate relationship from Provider: <" +
                                        to_parent.name +
                                        "> to Allocation: " + str(type(child)))
                    parent_role_name = parent_mapper.class_.__name__  # default TODO design review
                    parent_role_name = each_relationship.back_populates
                    parent_reln_to_child_db = each_relationship
        if parent_role_name is None:
            raise Exception("Missing relationship from Parent Provider: <" +
                            to_parent.name +
                            "> to child Allocation: " + str(type(child)) + " of class: " + child.__class__.__name__)
        setattr(child, parent_role_name, to_parent.row)
        child_mapper = object_mapper(self.row)
        parent_role_def = child_mapper.relationships.get(parent_role_name)  # found Project, model has project
        for each_fk_attr in parent_role_def.local_columns:
            if is_copy == False and getattr(self.row, each_fk_attr.name) is not None:
                self.log(f'Note: link child to parent - {parent_role_name} ({each_fk_attr.name} not None... fixing')
            setattr(self.row, each_fk_attr.name, None)
        return True

    def _get_child_role(self, child_cass_name, parent_role_name) -> str:
        """ given parent_role_name, return child_role_name """
        parent_mapper = object_mapper(self.row)  # , eg, Order cascades ShippedDate => OrderDetailList
        parent_relationships = parent_mapper.relationships
        found = False
        for each_parent_relationship in parent_relationships:  # eg, order has parents cust & emp, child orderdetail
            if each_parent_relationship.direction == sqlalchemy.orm.interfaces.ONETOMANY:  # cust, emp
                each_parent_role_name = each_parent_relationship.back_populates  # eg, OrderList
                if each_parent_role_name == parent_role_name and self.name == child_cass_name:
                    child_role_name = each_parent_relationship.key
                    return child_role_name
        raise Exception("unable to find child role corresponding to: " + parent_role_name)

    def _cascade_delete_children(self):
        """
        This recursive descent is required to adjust dependent sums/counts on passive_deletes; ie,

        when (and only when) the DBMS - and *not* SQLAlchemy - does the deletes.

        (When SQLAlchemy does deletes, these are queued through the normal delete logic.)
        @see nw/tests/test_dlt_order.py
        """

        parent_mapper = object_mapper(self.row)
        my_relationships = parent_mapper.relationships
        for each_relationship in my_relationships:  # eg, order has child OrderDetail
            if each_relationship.direction == sqlalchemy.orm.interfaces.ONETOMANY:  # eg, OrderDetail
                child_role_name = each_relationship.key  # eg, OrderList
                if each_relationship.cascade.delete and each_relationship.passive_deletes:
                    child_rows = getattr(self.row, child_role_name)
                    for each_child_row in child_rows:
                        old_child = self._make_copy(each_child_row)
                        each_child_logic_row = LogicRow(row=each_child_row,
                                                        old_row=old_child,
                                                        ins_upd_dlt="dlt",
                                                        nest_level=1 + self.nest_level,
                                                        a_session=self.session,
                                                        row_sets=self.row_sets)
                        each_child_logic_row.delete(reason="Cascade Delete to run rules on - " + child_role_name,
                                                    do_not_adjust=self)
                        self.session.delete(each_child_row)  # deletes in beforeFlush are not re-queued
        enforce_cascade = False
        if enforce_cascade:  # disabled - SQLAlchemy DOES enforce cascade delete/nullify; prevent way less important
            """
            per parent_cascade rule(s), nullify (child FKs), delete (children), prevent (if children exist)

            Default is ParentCascadeAction.PREVENT.

            This recursive descent is required to adjust dependent sums/counts.
            """
            list_parent_cascade_rules = rule_bank_withdraw.rules_of_class(self, ParentCascade)
            defined_relns = {}
            for each_parent_cascade_rule in list_parent_cascade_rules:
                defined_relns[each_parent_cascade_rule._relationship] = each_parent_cascade_rule
            for each_relationship in my_relationships:  # eg, Order has child OrderDetail
                if each_relationship.direction == sqlalchemy.orm.interfaces.ONETOMANY:  # eg, OrderDetail
                    each_child_role_name = each_relationship.key  # eg, OrderDetailList
                    refinteg_action = ParentCascadeAction.PREVENT
                    if each_child_role_name in defined_relns:
                        refinteg_action = defined_relns[each_child_role_name]._action
                    child_rows = getattr(self.row, each_child_role_name)
                    for each_child_row in child_rows:
                        old_child = self._make_copy(each_child_row)
                        each_child_logic_row = LogicRow(row=each_child_row,
                                                        old_row=old_child,
                                                        ins_upd_dlt="dlt",
                                                        nest_level=1 + self.nest_level,
                                                        a_session=self.session,
                                                        row_sets=self.row_sets)

                        if refinteg_action == ParentCascadeAction.DELETE:  # each_relationship.cascade.delete:
                            each_child_logic_row.delete(reason="Cascade Delete - " + each_child_role_name)

                        elif refinteg_action == ParentCascadeAction.NULLIFY:
                            for p, c in each_relationship.local_remote_pairs:
                                setattr(each_child_row, c.name, None)
                            each_child_logic_row.update(reason="Cascade Nullify - " + each_child_role_name)

                        elif refinteg_action == ParentCascadeAction.PREVENT:
                            msg = "Delete rejected - " + each_child_role_name + " has rows"
                            ll = RuleBank()
                            if ll.constraint_event:
                                ll.constraint_event(message=msg, logic_row=self, constraint=None)
                            raise ConstraintException(msg)
                        else:
                            raise Exception("Invalid parent_cascade action: " + refinteg_action)

    def _is_primary_key_changed(self) -> bool:
        meta = self.table_meta
        if hasattr(meta, "primary_key"):
            pk_columns = meta.primary_key.columns
        else:
            pk_columns = meta.mapper.mapped_table.primary_key.columns
        if len(pk_columns) == 0:
            raise Exception("No Primary Key: " + self.__str__())
        for each_pk_column in pk_columns:
            each_child_column_name = each_pk_column.name
            if getattr(self.row, each_child_column_name) != getattr(self.old_row, each_child_column_name):
                return True
        return False

    def _get_derived_attributes(self) -> List[InstrumentedAttribute]:
        """
            returns a list of derived attributes

            Example:
                def handle_all(logic_row: LogicRow):
                    row = logic_row.row
                    if logic_row.ins_upd_dlt == "ins" and hasattr(row, "CreatedOn"):
                        row.CreatedOn = datetime.datetime.now()
                        logic_row.log("early_row_event_all_classes - handle_all sets 'Created_on"'')

                    if logic_row.nest_level == 0:  # client updates should not alter derivations
                        derived_attributes = logic_row.get_derived_attributes()
                        if logic_row.are_attributes_changed(derived_attributes):
                            # NOTE: this does not trigger constraint_event registered in activate
                            raise ConstraintException("One or more derived attributes are changed")
        """
        result_derived_attrs = []
        derivations = rule_bank_withdraw.rules_of_class(self, Derivation)
        for each_derivation in derivations:
            result_derived_attrs.append(each_derivation._derive)
        return result_derived_attrs

    def are_attributes_changed(self, attr_list: List[InstrumentedAttribute]):
        """
        returns list of actually changed attr names (or empty list)

        Example
            if logic_row.are_attributes_changed([Employee.Salary, Employee.Title]):
                copy_to_logic_row = logic_row.new_logic_row(EmployeeAudit)
                copy_to_logic_row.link(to_parent=logic_row)  # link to parent Employee
                copy_to_logic_row.set_same_named_attributes(logic_row)
                copy_to_logic_row.insert(reason="Manual Copy " + copy_to_logic_row.name)  # triggers rules...

        if not logic_row.are_attributes_changed([Employee.Salary, Employee.Title])

        Args:
            attr_list: list of mapped attribute names (see example above)
        """
        changes = []
        if self.ins_upd_dlt == "upd":
            for each_attr in attr_list:
                if getattr(self.row, each_attr.key) != getattr(self.old_row, each_attr.key):
                    changes.append(each_attr.key)
        return changes

    def copy_children(self, copy_from: base, which_children: (dict or list)):
        """
        Useful in row event handlers to copy multiple children types to self from copy_from children.

        child-spec := < ‘child-list-name’ | < ‘child-list-name = parent-list-name’ >
        child-list-spec := [child-spec | (child-spec, child-list-spec)]

        Eg. RowEvent on Order
            which = ["OrderDetailList"]
            logic_row.copy_children(copy_from=row.parent, which_children=which)

        Eg, test/copy_children:
            child_list_spec = [
                ("MileStoneList",
                    ["DeliverableList"]  # for each Milestone, get the Deliverables
                ),
                "StaffList"
            ]
        """
        if self.nest_level == 0:
            self.log("Begin copy_children")
        which_children_list = which_children
        if isinstance(which_children, dict):  # prefer lists, but handle dict (initial version)
            which_children_list = []
            for item in which_children.items():
                child_spec = item[0]
                if item[1]:
                    child_spec += f' = {item[1]}'
                which_children_list.append(child_spec)
        copy_count = 0
        for each_item in which_children_list:
            copy_count += 1
            child_spec = each_item
            if type(each_item) is tuple:
                child_spec = each_item[0]
            copy_from_list_name = child_spec
            copy_to_list_name = child_spec
            equal_index = child_spec.find("=")
            if equal_index > 0:
                copy_to_list_name = child_spec[0, equal_index].strip()
                copy_from_list_name = child_spec[equal_index:].strip()
            copy_from_children = getattr(copy_from, copy_from_list_name)
            child_count = 0
            my_mapper = object_mapper(self.row)
            copy_to_role_def = my_mapper.relationships.get(copy_to_list_name)
            copy_to_class = copy_to_role_def.entity.class_
            for each_from_row in copy_from_children:
                # self.log(f'copy_children: {copy_from_list_name}[{child_count}] = {each_from_row}')
                each_from_logic_row = LogicRow(row=each_from_row, old_row=each_from_row,
                                               ins_upd_dlt="*", nest_level=0,
                                               a_session=self.session,
                                               row_sets=None)
                new_copy_to_row = LogicRow(row=copy_to_class(), old_row=copy_to_class(),
                                           ins_upd_dlt="ins",
                                           nest_level=self.nest_level + 1,
                                           a_session=self.session,
                                           row_sets=self.row_sets)
                new_copy_to_row.set_same_named_attributes(each_from_logic_row)
                new_copy_to_row.link(to_parent=self, is_copy=True)
                new_copy_to_row.insert(reason="Copy Children " + copy_to_list_name)  # triggers rules...
                if type(each_item) is tuple:
                    new_copy_to_row.copy_children(each_from_row, each_item[1])
        if self.nest_level == 0:
            self.log(f'End copy_children - {copy_count} copied')

    def set_same_named_attributes(self, from_logic_row: 'LogicRow'):
        """
        copy like-named values from from_logic_row -> self

        Example
            if logic_row.are_attributes_changed([Employee.Salary, Employee.Title]):
                copy_to_logic_row = logic_row.new_logic_row(EmployeeAudit)
                copy_to_logic_row.link(to_parent=logic_row)  # link to parent Employee
                copy_to_logic_row.set_same_named_attributes(logic_row)
                copy_to_logic_row.insert(reason="Manual Copy " + copy_to_logic_row.name)  # triggers rules...

        Args:
            from_logic_row: source of copy (to self)

        """
        row_mapper = object_mapper(self.row)
        if self.row.__tablename__ == "Customerxx":
            print("Debug Stop here")
            # TODO - check use of LogicRow (using row_mapper.column_attrs??  vs attrs)
        from_attrs = object_mapper(from_logic_row.row).column_attrs
        for each_attr in row_mapper.column_attrs:  # avoid parent objects, child collections
            is_hybrid = isinstance(each_attr, hybrid_property)
            each_attr_name = self._get_attr_name(mapper=row_mapper, attr=each_attr)
            if each_attr_name is None:  # parent or child-list
                raise Exception(
                    "Note; set_same_named_attributes -- attr_name is None, should not occur for row_mapper.column_attrs")
            else:
                if each_attr_name in self.table_meta.primary_key.columns.keys():
                    debug_skip_primary_key_columns = True
                elif rule_bank_withdraw.is_attr_derived(class_name=self.row.__tablename__, attr_name=each_attr_name):
                    debug_skip_derived_columns = True
                else:
                    if each_attr_name in from_attrs:
                        setattr(self.row, each_attr_name, getattr(from_logic_row.row, each_attr_name))
        return

    def _get_old_child_rows(self, relationship: RelationshipProperty):
        """
        result = getattr(self.old_row, role_name)  # even with util.use_transient, yields nothing, unsure why
        """

        child_filter = {}
        for p, c in relationship.local_remote_pairs:
            child_filter[c.name] = getattr(self.old_row, p.name)
        result = self.session.query(relationship.mapper.entity).filter_by(**child_filter).all()
        return result

    def _parent_cascade_pk_change(self):  # ???
        """
        cascade pk change (if any) to children, unconditionally.

        Presumption: children ref the same pKey (vs. some other "candidate key")
        """
        if self._is_primary_key_changed():
            list_parent_cascade_rules = rule_bank_withdraw.rules_of_class(self, ParentCascade)
            defined_relns = {}
            for each_parent_cascade_rule in list_parent_cascade_rules:
                defined_relns[each_parent_cascade_rule._relationship] = each_parent_cascade_rule
            parent_mapper = object_mapper(self.row)
            my_relationships = parent_mapper.relationships
            for each_relationship in my_relationships:  # eg, order has parents cust & emp, child orderdetail
                if each_relationship.direction == sqlalchemy.orm.interfaces.ONETOMANY:  # cust, emp
                    reason = "Cascading PK change to: " + \
                             each_relationship.backref + "->" + \
                             each_relationship.key
                    child_rows = self._get_old_child_rows(relationship=each_relationship)
                    for each_child_row in child_rows:
                        old_child = self._make_copy(each_child_row)
                        each_child_logic_row = LogicRow(row=each_child_row, old_row=old_child, ins_upd_dlt="upd",
                                                        nest_level=1 + self.nest_level,
                                                        a_session=self.session, row_sets=self.row_sets)
                        for p, c in each_relationship.local_remote_pairs:
                            setattr(each_child_row, c.name, getattr(self.row, p.name))
                        each_child_logic_row.update(reason=reason)

        return self

    def _parent_cascade_attribute_changes_to_children(self):
        """
        Child Formulas can reference (my) Parent Attributes, so...

        If the *referenced* Parent Attributes are changed, cascade to child

        Setting update_msg to denote parent_role

        This will cause each child to recompute all formulas referencing that role

        eg, cascade from Order:
        * OrderDetail.ShippedDate = Order.ShippedDate, so....
        * Order cascades changed Order.ShippedDate => Order.OrderDetailList

        Todo: test cascade to multiple children using same parent role name, in alternating order
        """

        referring_children_dict = rule_bank_withdraw.get_referring_children(parent_logic_row=self)
        ''' eg, { 'Order' : [ ( 'OrderDetail', 'OrderDetailList', 'ShippedDate', 'Order' ) ] } '''

        referring_children = referring_children_dict.get(self.name)
        """  eg, [ ( 'OrderDetail', 'OrderDetailList', 'ShippedDate', 'Order' ) ] """

        if referring_children is None:
            pass  # not referenced by child formulas, no rules, etc...
        else:
            cascade_dict = dict()
            """ set of (child_role_name, attrname) (eg, OrderDetailList, ShippedDate) that we will cascade to """

            for each_child_class_name, each_child_role_name, each_parent_attribute_name, each_parent_role_name in referring_children:  # children that reference me
                value = getattr(self.row, each_parent_attribute_name)
                old_value = getattr(self.old_row, each_parent_attribute_name)
                if value != old_value:
                    # child_role_name = self._get_child_role(each_parent_role_name[0], each_parent_role_name[1])
                    if each_child_role_name not in cascade_dict:
                        cascade_dict[each_child_role_name] = (each_child_role_name, each_parent_attribute_name, each_parent_role_name)

            for each_child_role_name, each_parent_attribute_name, each_parent_role_name in cascade_dict.values():
                reason = "Cascading " + each_parent_role_name + "." + each_parent_attribute_name + " (,...)"
                """ this is *not* just text!  it drives is_parent_cascading.  LB test: OrderHeader (not Order) """
                child_rows = getattr(self.row, each_child_role_name)
                for each_child_row in child_rows:
                    old_child = self._make_copy(each_child_row)
                    each_logic_row = LogicRow(row=each_child_row, old_row=old_child, ins_upd_dlt="upd",
                                            nest_level=1 + self.nest_level,
                                            a_session=self.session, row_sets=self.row_sets)
                    # no need to set attrs - the child will do that
                    # NB: the reason contains the parent_role_name, used to prevent pruning
                    each_logic_row.update(reason=reason)
        pass
        
    def _is_parent_cascading(self, parent_role_name: str):
        """ if so (check self.reason), we must not prune referencing formulae """
        result = False
        update_reason = self.reason
        if update_reason.startswith("Cascading "):
            target = update_reason[10:]
            words = target.split('.')
            cascading_parent_role_name = words[0]
            if cascading_parent_role_name == parent_role_name:
                result = True
        return result

    def _is_different_parent(self, parent_role_name: str) -> bool:
        """ return True if any changes to foreign key fields of parent_role_name"""
        role_def = self._get_parent_role_def(parent_role_name=parent_role_name)
        row = self.row
        old_row = self.old_row
        if old_row is None:
            return True
        else:
            for each_child_col, each_parent_col in role_def.local_remote_pairs:
                each_child_col_name = each_child_col.key
                if getattr(row, each_child_col_name) != getattr(old_row, each_child_col_name):
                    return True
            return False

    def _is_formula_pruned(self, formula: Formula) -> bool:
        """
        Prune Conservatively:
         * if delete, or
         * has parent refs & no dependencies changed (skip parent read)
        e.g. always execute formulas with no dependencies
        """
        result_prune = True
        row = self.row
        old_row = self.old_row
        if self.ins_upd_dlt == "ins":
            result_prune = False
        elif self.ins_upd_dlt == "dlt":
            result_prune = True
        else:
            is_parent_changed = False
            is_dependent_changed = False
            for each_dependency in formula._dependencies:
                column = each_dependency
                if '.' in column:
                    role_name = column.split(".")[0]
                    if self._is_different_parent(parent_role_name=role_name):
                        is_parent_changed = True
                        break
                    if self._is_parent_cascading(role_name):
                        is_parent_changed = True
                        break
                else:
                    if getattr(row, column) != getattr(old_row, column):
                        is_dependent_changed = True
                        break
            result_prune = not (is_parent_changed or is_dependent_changed)
        if result_prune:
            log_text = "Prune Formula: " + formula._column + " [" + str(formula._dependencies) + "]"
            if formula._no_prune:  # e.g., no attributes referenced, such as time/date stamp
                result_prune = False
                log_text = log_text.replace("Prune", "Pruned Formula retained per no_prune")
            self.log(log_text)
        return result_prune

    def _formula_rules(self):
        """ execute un-pruned formulae, in dependency order """
        self.log_engine("formula_rules")
        formula_rules = rule_bank_withdraw.rules_of_class(self, Formula)
        formula_rules.sort(key=lambda formula: formula._exec_order)
        for each_formula in formula_rules:
            if not self._is_formula_pruned(each_formula):
                each_formula.execute(self)

    def _constraints(self):
        """ execute constraints (throw error if one fails) """
        # self.log("constraints")
        constraint_rules = rule_bank_withdraw.rules_of_class(self, Constraint)
        for each_constraint in constraint_rules:
            each_constraint.execute(self)

    def _is_inserted_parent(self, relationship: sqlalchemy.orm.relationships) -> bool:
        """insert parent if any aggregate on this relationship has insert_parent

        Invoked from _load_parents_on_insert() when parent is missing

        Args:
            relationship (sqlalchemy.orm.relationships): _description_
        Returns:
            True if parent inserted
        """
        has_inserted_parent = False
        aggregate_rules = rule_bank_withdraw.aggregate_rules(child_logic_row=self)
        for each_parent_role, each_aggr_list in aggregate_rules.items():
            for each_aggregate in each_aggr_list:
                if each_aggregate._parent_role_name == relationship.key and each_aggregate.insert_parent:
                    has_inserted_parent = True  # ok, we create it...
                    self.log(f'Insert Parent: {each_aggregate._parent_role_name}')
                    local_remote_pairs = relationship.local_remote_pairs
                    if len(local_remote_pairs) == 0:
                        raise Exception("Malformed relationship has no foreign key: " +
                                        str(relationship))
                    copy_to_class = relationship.entity.class_
                    inserted_parent_row = LogicRow(row=copy_to_class(), old_row=copy_to_class(),
                                                   ins_upd_dlt="ins",
                                                   nest_level=self.nest_level + 1,
                                                   a_session=self.session,
                                                   row_sets=self.row_sets)
                    setattr(self.row, each_aggregate._parent_role_name, inserted_parent_row.row)  # parent setter
                    # self.link(to_parent=inserted_parent_row.row, is_copy=True)
                    for each_child_column, each_parent_column in local_remote_pairs:
                        val = getattr(self.row, each_child_column.name)
                        setattr(inserted_parent_row.row, each_parent_column.name, val)
                        pass
                    inserted_parent_row.insert(reason=f'Insert Parent from {self.name}')
                    break
        return has_inserted_parent

    def _is_foreign_key_null(self, relationship: sqlalchemy.orm.relationships) -> bool:
        """

        Args:
            relationship (sqlalchemy.orm.relationships): _description_

        Raises:
            Exception: _description_

        Returns:
            bool: True if any fk attrs are null
        """
        child_columns = relationship.local_columns
        if len(child_columns) == 0:
            raise Exception("Malformed relationship has no foreign key: " +
                            str(relationship))
        for each_child_column in child_columns:
            each_child_column_name = each_child_column.name
            if getattr(self.row, each_child_column_name) is None:
                return True
        return False

    def _eager_defaults(self):
        """called by insert() to set column server defaults for nulls, constants only

        TODO - consider defaulting sums and counts to 0.
        * Failure can make insert Fail (Airplane: row.passenger_count <= row.capacity)
        * Seems pretty obvious, not sure why this was not done.

        thanks to Elmer de Looff: https://variable-scope.com/posts/setting-eager-defaults-for-sqlalchemy-orm-models
        """
        mapper = inspect(self.row).mapper
        defaults: dict = {}
        defaults_skipped = ""
        for each_column in mapper.columns:
            if each_column.name == 'RegistrationDate':
                debug_stop = "convenient break"
            try:
                if isinstance(each_column, sqlalchemy.sql.schema.Column) and each_column.server_default is not None:
                    if (default_str := getattr(each_column.server_default, "arg")) is not None:
                        if isinstance(default_str, sqlalchemy.sql.elements.TextClause):
                            default_str = default_str.text
                        default = default_str  # but, need to convert for type...
                        if not callable(default) and not isinstance(default, Function) and default != 'NULL':
                            attr = mapper.get_property_by_column(each_column)
                            do_defaults = True  # for debug
                            if do_defaults:
                                if isinstance(each_column.type, sqlalchemy.sql.sqltypes.Integer):
                                    default = int(default_str)
                                    if isinstance(each_column.type, sqlalchemy.sql.sqltypes.Numeric):
                                        default = int(default_str)
                                elif isinstance(each_column.type, sqlalchemy.sql.sqltypes.String):
                                    default = default_str  # it's not quoted
                                elif isinstance(each_column.type, sqlalchemy.sql.sqltypes.Float):
                                    default = float(default_str)
                                elif isinstance(each_column.type, sqlalchemy.sql.sqltypes.DECIMAL):
                                    default = Decimal(default)
                                # elif isinstance(each_column.type, sqlalchemy.sql.sqltypes.Boolean):
                                # default = bool(default_str)
                                elif isinstance(each_column.type, sqlalchemy.sql.sqltypes.DateTime):
                                    if default == "CURRENT_TIMESTAMP":
                                        default = date.today()
                                    else:
                                        defaults_skipped += f'{each_column.name}[{each_column.type} (unexpected default: {default})] '
                                        default = None
                                elif isinstance(each_column.type, sqlalchemy.sql.sqltypes.Date):
                                    if default == "CURRENT_TIMESTAMP":
                                        default = date.today()
                                    else:
                                        defaults_skipped += f'{each_column.name}[{each_column.type} (unexpected default: {default})] '
                                        default = None
                                # elif isinstance(each_column.type, sqlalchemy.sql.sqltypes.Binary):
                                #    default = default
                                else:
                                    default = None
                                    # self.log(f'Warning - default ignored for {self.name}.{each_column.name}: {each_column.type}')
                                    defaults_skipped += f'{each_column.name}[{each_column.type} (not handled)] '
                            defaults[attr.key] = default
            except Exception as ex:
                defaults_skipped += f'{each_column.name}[{each_column.type}] (ex: {ex}) '

        defaults_applied = ""
        for attr, value in defaults.items():
            if getattr(self.row, attr) is None:
                setattr(self.row, attr, value)
                defaults_applied += f"{attr} "
        if defaults_applied != "" or defaults_skipped != "":
            default_msg = f'server_defaults: {defaults_applied}'
            if defaults_skipped != "":
                default_msg += f"-- skipped: {defaults_skipped}"
            self.log(f'{default_msg}')
        return

    def _load_parents_on_insert(self):
        """ sqlalchemy lazy does not work for inserts... do it here because...
        1. RI would require the sql anyway
        2. Provide a consistent model - your parents are always there for you
            - eg, see add_order event rule - references {sales_rep.Manager.FirstName}
        """

        ref_integ_enabled = True
        list_ref_integ_rules = rule_bank_withdraw.rules_of_class(self, ParentCheck)
        if list_ref_integ_rules:
            ref_integ_rule = list_ref_integ_rules[0]

        child_mapper = object_mapper(self.row)
        my_relationships = child_mapper.relationships
        for each_relationship in my_relationships:  # eg, order has parents cust & emp, child orderdetail
            if each_relationship.direction == sqlalchemy.orm.interfaces.MANYTOONE:  # cust, emp
                parent_role_name = each_relationship.key  # eg, OrderList
                if self._is_foreign_key_null(each_relationship):
                    pass  # 
                else:
                    # continue - foreign key not null - parent *should* exist
                    self._get_parent_logic_row(parent_role_name)  # sets the accessor
                    does_parent_exist = getattr(self.row, parent_role_name)
                    if does_parent_exist:
                        pass  # yes, parent exists... it's all fine
                    else:  # no, maybe we create it...
                        does_parent_exist = self._is_inserted_parent(each_relationship)
                    if does_parent_exist:
                        pass  # exists (possibly created - all is fine)
                    elif ref_integ_enabled:
                        msg = "Missing Parent: " + parent_role_name
                        self.log(msg)
                        ll = RuleBank()
                        if ll.constraint_event:
                            ll.constraint_event(message=msg, logic_row=self, constraint=None)
                        raise ConstraintException(msg)
                    else:
                        self.log("Warning: Missing Parent: " + parent_role_name)
                        pass  # refinteg *should catch* - if not enabled you must not care
        return self

    def _check_parents_on_update(self):
        """ per ParentCheck rule, verify parents exist.

        If disabled, ignore (with warning).
        """

        list_ref_integ_rules = rule_bank_withdraw.rules_of_class(self, ParentCheck)
        if list_ref_integ_rules:
            ref_integ_rule = list_ref_integ_rules[0]
            if ref_integ_rule._enable:
                child_mapper = object_mapper(self.row)
                my_relationships = child_mapper.relationships
                for each_relationship in my_relationships:  # eg, order has parents cust & emp, child orderdetail
                    if each_relationship.direction == sqlalchemy.orm.interfaces.MANYTOONE:  # cust, emp
                        parent_role_name = each_relationship.key  # eg, OrderList
                        if not self._is_foreign_key_null(each_relationship):
                            # continue
                            reason = "Cascading PK change to: " + \
                                     each_relationship.key + "->" + \
                                     each_relationship.back_populates
                            if self.reason == reason:
                                """
                                The parent doing the cascade obviously exists,
                                and note: try to getattr it will fail
                                (FIXME design review - perhaps SQLAlchemy is not checking cache?)
                                """
                                pass
                            else:
                                self._get_parent_logic_row(parent_role_name)  # sets the accessor
                                does_parent_exist = getattr(self.row, parent_role_name)
                                if does_parent_exist is None and ref_integ_rule._enable == True:
                                    if self._is_inserted_parent(relationship=each_relationship):
                                        pass  # inserted
                                    else:
                                        msg = "Missing Parent: " + parent_role_name
                                        self.log(msg)
                                        ll = RuleBank()
                                        if ll.constraint_event:
                                            ll.constraint_event(message=msg, logic_row=self, constraint=None)
                                        raise ConstraintException(msg)
                                else:
                                    self.log("Warning: Missing Parent: " + parent_role_name)
                                    pass  # refinteg *should catch* - if not enabled you must not care
        return self

    def _is_in_list(self, logic_rows: List) -> bool:
        """
        e.g., for do_not_adjust_list, find out if logic_row is in it
        """
        result = False
        if logic_rows is not None:
            meta = self.table_meta
            pkey_cols = meta.primary_key.columns
            for each_logic_row in logic_rows:
                same_row = True
                for each_column in meta.primary_key.columns:
                    col_name = each_column.name
                    if getattr(self.row, col_name) != getattr(each_logic_row.row, col_name):
                        same_row = False
                        break
                if same_row:
                    result = True
        return result

    def _adjust_parent_aggregates(self, do_not_adjust_list=None):
        """
        Chain to parents - adjust aggregates (sums, counts)

        Objective: 1 (one) update per role, for N aggregates along that role.

        For each child-to-parent role,
            For each aggregate along that role
                execute sum (etc) logic which set parent_adjustor (as req'd)
            use parent_adjustor to save altered parent (iff req'd)
        """
        # self.log("adjust_parent_aggregates")
        aggregate_rules = rule_bank_withdraw.aggregate_rules(child_logic_row=self)
        for each_parent_role, each_aggr_list in aggregate_rules.items():
            parent_adjuster = ParentRoleAdjuster(child_logic_row=self,
                                                 parent_role_name=each_parent_role)
            for each_aggregate in each_aggr_list:  # adjusts each_parent iff req'd
                each_aggregate.adjust_parent(parent_adjuster, do_not_adjust_list=do_not_adjust_list)
            parent_adjuster.save_altered_parents(do_not_adjust_list=do_not_adjust_list)  # iff req'd (altered only)

    def user_row_update(self, row: base, ins_upd_dlt: str) -> 'LogicRow':
        """
        returns a created LogicRow from a SQLAlchemy row,
        to support LogicRow.insert/update/delete

        Args:
            row: SQLAlchemy row
            ins_upd_dlt: supplied by LogicRow.insert/update/delete

        Returns:
            LogicRow

        """
        result_logic_row = LogicRow(row=row,
                                    old_row=self._make_copy(row),
                                    nest_level=self.nest_level + 1,
                                    a_session=self.session,
                                    row_sets=self.row_sets,
                                    ins_upd_dlt=ins_upd_dlt)
        return result_logic_row

    def early_row_event_all_classes(self, verb_reason: str):
        """
        if exists: rules_bank._early_row_event_all_classes(self)

        Args:
            verb_reason: debug string (not used)

        Returns:

        """
        rules_bank = RuleBank()
        if rules_bank._early_row_event_all_classes is not None:
            # self.log("early_row_event_all_classes - " + verb_reason)
            rules_bank._early_row_event_all_classes(self)

    def update(self, reason: str = None, row: base = None):
        """
        make updates - with logic - in events, for example

        Example
            row = sqlalchemy read
            logic_row.update(row=row, msg="my log message")

        Args:
            reason: message inserted to to logging
            row: either a LogicRow, or a SQLAlchemy row
        """
        if row is not None:  # e.g., event code reads/updates SQLAlchemy row
            user_logic_row = self.user_row_update(row=row, ins_upd_dlt="upd")
            user_logic_row.update(reason=reason)
        else:
            self.reason = reason
            self.log("Update - " + reason)
            self.early_row_event_all_classes("Update - " + reason)
            self._early_row_events()
            self._check_parents_on_update()
            self._copy_rules()
            self._formula_rules()
            self._adjust_parent_aggregates()  # parent chaining (sum / count adjustments)
            self._constraints()
            self._parent_cascade_attribute_changes_to_children()  # child chaining (cascade changed parent references)
            self._parent_cascade_pk_change()  # actions - delete, nullify, prevent
            if self.row_sets is not None:  # required for adjustment logic (see dragons)
                self.row_sets.add_processed_logic(logic_row=self)  # used in commit logic
            self._row_events()
            if self.row_sets is not None:  # eg, for debug as in upd_order_shipped test
                self.row_sets.remove_submitted(logic_row=self)

    def insert(self, reason: str = None, row: base = None):
        """
        make inserts - with logic - in events, for example

        Example
            row = mapped_class()
            logic_row.insert(row=row, msg="my log message")

        Args:
            reason: message inserted to logging
            row: either a LogicRow, or a SQLAlchemy row
        """

        if row is not None:  # user inserting mapped class, not logic_row... make one.
            user_logic_row = self.user_row_update(row=row, ins_upd_dlt="ins")
            user_logic_row.insert(reason=reason)
        else:
            self.reason = reason
            self.log("Insert - " + reason)
            self.early_row_event_all_classes("Insert - " + reason)
            self._eager_defaults()
            self._load_parents_on_insert()
            self._early_row_events()
            self._copy_rules()
            self._formula_rules()
            self._adjust_parent_aggregates()
            self._constraints()
        if self.row_sets is not None:  # required for adjustment logic (see dragons)
            self.row_sets.add_processed_logic(logic_row=self)  # used in commit logic
            self._row_events()
        if self.row_sets is not None:  # eg, for debug as in upd_order_shipped test
            self.row_sets.remove_submitted(logic_row=self)

    def delete(self, reason: str = None, row: base = None, do_not_adjust_list=None):
        """
        make deletes - with logic - in events, for example

        Example
            row = sqlalchemy read
            logic_row.delete(row=row, msg="my log message")

        Args:
            reason: message inserted to to logging
            row: either a LogicRow, or a SQLAlchemy row
            base: unused
            deleting_along: RelationshipProperty (=> bypass adjustments)
        """
        if row is not None:
            user_logic_row = self.user_row_update(row=row, ins_upd_dlt="ins")
            user_logic_row.insert(reason=reason)
        else:
            self.reason = reason
            self.log("Delete - " + reason)
            self.early_row_event_all_classes("Delete - " + reason)
            self._early_row_events()
            self._adjust_parent_aggregates(do_not_adjust_list=do_not_adjust_list)
            self._constraints()
            self._cascade_delete_children()
            self.row_sets.add_processed_logic(logic_row=self)  # used in commit logic


class ParentRoleAdjuster:
    """
    Contains child_logic_row and current / previous parent_logic_row
        Set iff parent needs adjustment
    and method to save_altered_parents.

    Instances are passed to <aggregate>.adjust_parent who will set parent row(s) values
    iff adjustment is required (e.g., summed value changes, where changes, fk changes, etc)
    This ensures only 1 update per set of aggregates along a given role
    """

    def __init__(self, parent_role_name: str, child_logic_row: LogicRow):

        self.child_logic_row = child_logic_row  # the child (curr, old values)

        self.parent_role_name = parent_role_name  # which parent are we dealing with?
        self.parent_logic_row = None
        self.previous_parent_logic_row = None
        self.adjusting_attributes = ""
        """ list of attributes being adjusted, for log """

    def append_adjusting_attributes(self, attribute_name: str):
        if self.adjusting_attributes == "":
            self.adjusting_attributes = attribute_name
        else:
            self.adjusting_attributes += f', {attribute_name}'

    def save_altered_parents(self, do_not_adjust_list: List = None):
        """
        Save (chain) parent iff parent_logic_row has been set by sum/count executor.
        This can update parent, and previous parent (ie, foreign key changed)

        Dragons lurk herein
        ===================
            upd_order_reuse changes OrderDetail.ProductId, and Order.CustomerId
            listeners do not guarantee order
            Failures were seen for OrderDetail first
                It adjusted to the New Customer
            Fix is defer adjustment chaining logic iff the parent row is in the row_sets.submitted_row
                That is, the adjustment is done, but we don't run chaining logic (parent_logic_row.update())
                That's because the chaining logic will be run later in listeners (row_sets.submitted_row)

            Examples:
                upd_order_reuse - occurs half time, see listeners-bug_explore to force
                test_add_order
                    first, note OrderDetails are **sometimes** processed before Order (it varies!)
                    it's easy when the order is first
                    if OrderDetail is first then "debug_info" will see....
                        do_defer_adjustment: True, is_parent_submitted: True, is_parent_row_processed: False
                            adjustment occurs, but *not* the update() logic (since will occur when processed)
                ApiLogicServer - place_order.py, scenario: Clone Existing Order
                    the order is first (only), so requires do_defer_adjustment is false, so...
                    do_defer_adjustment: False, is_parent_submitted: True, is_parent_row_processed: True
        """
        if self.parent_logic_row is None:  # save *only altered* parents (often does nothing)
            pass
            # self.child_logic_row.log("adjust not required for parent_logic_row: " + str(self))
        else:
            parent_logic_row = self.parent_logic_row
            row_sets = parent_logic_row.row_sets
            parent_row_debug = self.parent_logic_row.row
            is_parent_submitted = parent_logic_row.row in row_sets.submitted_row
            is_parent_row_processed = parent_logic_row.row in row_sets.processed_rows
            do_defer_adjustment = is_parent_submitted and not is_parent_row_processed
            if self.child_logic_row.name == 'OrderDetailXX':
                self.child_logic_row.log(f'do_defer_adjustment: {do_defer_adjustment}'
                                         f', is_parent_submitted: {is_parent_submitted}'
                                         f', is_parent_row_processed: {is_parent_row_processed}')
                debug_info = "target child defer adjustment check..."
            enable_deferred_adjusts = True
            if do_defer_adjustment and enable_deferred_adjusts:  # see dragon alert, above
                self.parent_logic_row.log(f'Adjustment logic chaining deferred for this parent parent '
                                          f'do_defer_adjustment: {do_defer_adjustment}'
                                          f', is_parent_submitted: {is_parent_submitted}'
                                          f', is_parent_row_processed: {is_parent_row_processed}, ' +
                                          self.parent_role_name)
                debug_info = "target child defer adjustment!"
            else:
                if do_defer_adjustment:  # just for debug when enable_deferred_adjusts is false
                    self.child_logic_row.log(
                        "Adjustment deferred DISABLED (DEBUG ONLY!!) for parent" + self.parent_role_name)
                is_do_not_adjust_deleted_parent = self.parent_logic_row._is_in_list(do_not_adjust_list)
                if is_do_not_adjust_deleted_parent:
                    self.child_logic_row.log(f'No adjustment on deleted parent: {self.parent_role_name}')
                else:
                    parent_logic_row.ins_upd_dlt = "upd"
                    parent_logic_row.update(
                        reason="Adjusting " + self.parent_role_name + ": " + self.adjusting_attributes)
                    # no after_flush: https://stackoverflow.com/questions/63563680/sqlalchemy-changes-in-before-flush-not-triggering-before-flush
        if self.previous_parent_logic_row is None:
            pass
            # self.child_logic_row.log("save-adjusted not required for previous_parent_logic_row: " + str(self))
        else:
            previous_parent_logic_row = self.previous_parent_logic_row
            if (previous_parent_logic_row.row_sets.is_submitted(previous_parent_logic_row.row)):
                self.child_logic_row.log("Adjustment deferred for previous parent:" + self.parent_role_name)
            else:
                current_session = self.child_logic_row.session
                previous_parent_logic_row.ins_upd_dlt = "upd"
                previous_parent_logic_row.update(reason="Adjusting Old " + self.parent_role_name)
