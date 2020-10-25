import sqlalchemy
from sqlalchemy import inspect
from sqlalchemy.ext.declarative import base
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import object_mapper, session, relationships

import logic_bank
from logic_bank.rule_bank.rule_bank import RuleBank
from sqlalchemy.ext.declarative import declarative_base

# from logic_bank.exec_row_logic.parent_role_adjuster import ParentRoleAdjuster
from logic_bank.rule_bank import rule_bank_withdraw
from logic_bank.rule_type.constraint import Constraint
from logic_bank.rule_type.formula import Formula
from logic_bank.rule_type.row_event import EarlyRowEvent


class LogicRow:
    """
    Wraps row and  old_row, plus methods for insert, update and delete - rule enforcement

    Passed to user logic, mainly to make updates - with logic, for example

        row = sqlalchemy read
        logic_row.update(row=row, msg="my log message")

    Additional instance variables: ins_upd_dlt, nest_level, session, etc.

    Helper Methods (get_parent_logic_row(role_name), log, etc)

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
        self.ins_upd_dlt_initial = ins_upd_dlt  # order inserted, then adjusted
        self.nest_level = nest_level
        self.reason = "?"  # set by insert, update and delete
        """ if starts with cascade, triggers cascade processing """

        self.row_sets = row_sets
        if row_sets is not None:  # eg, for debug as in upd_order_shipped test
            row_sets.add_processed(logic_row=self)

        rb = RuleBank()
        self.rb = rb
        self.session = rb._session
        self.engine = rb._engine
        self.some_base = declarative_base()

        self.name = type(self.row).__name__  # class name (not table name)
        self.table_meta = None
        if self.row is not None:
            if type(self.row).__name__ in row.metadata.tables:
                self.table_meta = row.metadata.tables[type(self.row).__name__]
            else:
                self.table_meta = inspect(self.row)
                self.log_engine("Restriction: Class Name must equal Table Name: " + self.name)
        if self.engine is not None:  # e.g, for testing legacy logic (no RuleBank)
            self.inspector = Inspector.from_engine(self.engine)

    def __str__(self):
        result = ".."
        for x in range(self.nest_level):
            result += ".."
        result += self.row.__tablename__ + "["
        my_meta = self.table_meta
        if not hasattr(my_meta, "primary_key"):
            result += "not available"
        else:   # my_meta.primary_key.columns.keys()
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
        for each_attr in row_mapper.all_orm_descriptors:
            is_hybrid = isinstance(each_attr, hybrid_property)
            each_attr_name = None
            if hasattr(each_attr, "name"):
                each_attr_name = each_attr.name
            elif isinstance(each_attr, hybrid_property):
                each_attr_name = each_attr.__name__
                # self.row.paid_order_count = 22
            if each_attr_name is None:  # parent or child-list
                pass   # don't print, don't even call (avoid sql)
            else:
                if not is_first:
                    result += ", "
                is_first = False
                if each_attr_name == "Idxx":
                    print("Debug Stop here")
                value = getattr(self.row, each_attr_name)
                result += each_attr_name + ": "
                old_value = value
                if self.old_row is not None:
                    old_value = getattr(self.old_row, each_attr_name)
                if value != old_value:
                    result += ' [' + str(old_value) + '-->] '
                if isinstance(value, str):
                    result += value
                else:
                    result += str(value)
        result += f'  row@: {str(hex(id(self.row)))}'
        return result  # str(my_dict)

    def log(self, msg: str):
        """
        prints to logic_logger: row/old_row, indented, inserting msg
        """
        output = str(self)
        output = output.replace("]:", "] {" + msg + "}", 1)
        logic_bank.logic_logger.debug(output)  # more on this later

    def log_engine(self, msg: str):
        """
        prints to engine_logger: row/old_row, indented, inserting msg
        """
        output = str(self)
        output = output.replace("]:", "] {" + msg + "}", 1)
        logic_bank.engine_logger.debug(output)

    def make_copy(self, a_row: base) -> base:
        """
        returns copy of row, or None

        :param a_row:
        :return:
        """
        result = None
        if a_row is not None:
            result_class = a_row.__class__
            result = result_class()
            row_mapper = object_mapper(a_row)
            for each_attr in row_mapper.columns:  # note skips parent references
                setattr(result, each_attr.key, getattr(a_row, each_attr.key))
        return result

    def get_parent_logic_row(self, role_name: str, from_row: base = None) -> 'LogicRow':
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
        old_parent = self.make_copy(parent_row)
        parent_logic_row = LogicRow(row=parent_row, old_row=old_parent, ins_upd_dlt="*", nest_level=1 + self.nest_level,
                                    a_session=self.session, row_sets=self.row_sets)
        return parent_logic_row

    def early_row_events(self):
        self.log_engine("early_events")
        early_row_events = rule_bank_withdraw.generic_rules_of_class(EarlyRowEvent)
        for each_row_event in early_row_events:
            each_row_event.execute(self)
        early_row_events = rule_bank_withdraw.rules_of_class(self, EarlyRowEvent)
        for each_row_event in early_row_events:
            each_row_event.execute(self)

    def copy_rules(self):
        """ runs copy rules (get parent values) """
        copy_rules = rule_bank_withdraw.copy_rules(self)
        for role_name, copy_rules_for_table in copy_rules.items():
            logic_row = self
            if logic_row.ins_upd_dlt == "ins" or \
                    logic_row.is_different_parent(parent_role_name=role_name):
                self.log("copy_rules for role: " + role_name)
                parent_logic_row = logic_row.get_parent_logic_row(role_name)
                for each_copy_rule in copy_rules_for_table:  # TODO consider orphans
                    each_copy_rule.execute(logic_row, parent_logic_row)

    def get_parent_role_def(self, parent_role_name: str):
        """ returns sqlalchemy role_def """
        my_mapper = object_mapper(self.row)
        role_def = my_mapper.relationships.get(parent_role_name)
        if role_def is None:
            raise Exception(f"FIXME invalid role name {parent_role_name}")
        return role_def

    def get_child_role(self, parent_role_name) -> str:
        """ given parent_role_name, return child_role_name """
        parent_mapper = object_mapper(self.row)  # , eg, Order cascades ShippedDate => OrderDetailList
        parent_relationships = parent_mapper.relationships
        found = False
        for each_parent_relationship in parent_relationships:  # eg, order has parents cust & emp, child orderdetail
            if each_parent_relationship.direction == sqlalchemy.orm.interfaces.ONETOMANY:  # cust, emp
                each_parent_role_name = each_parent_relationship.back_populates  # eg, OrderList
                if each_parent_role_name == parent_role_name:
                    child_role_name = each_parent_relationship.key
                    return child_role_name
        raise Exception("unable to find child role corresponding to: " + parent_role_name)

    def cascade_delete_children(self):
        """
        Find child relationships that are cascade delete, and delete the children.

        This recursive descent is required to adjust dependent sums/counts.
        """
        parent_mapper = object_mapper(self.row)
        my_relationships = parent_mapper.relationships
        for each_relationship in my_relationships:  # eg, cust has child OrderDetail
            if each_relationship.direction == sqlalchemy.orm.interfaces.ONETOMANY:  # eg, OrderDetail
                child_role_name = each_relationship.key  # eg, OrderList
                if each_relationship.cascade.delete:
                    child_rows = getattr(self.row, child_role_name)
                    for each_child_row in child_rows:
                        old_child = self.make_copy(each_child_row)
                        each_child_logic_row = LogicRow(row=each_child_row,
                                                        old_row=old_child,
                                                        ins_upd_dlt="dlt",
                                                        nest_level=1 + self.nest_level,
                                                        a_session=self.session,
                                                        row_sets=self.row_sets)
                        each_child_logic_row.delete(reason="Cascade Delete - " + child_role_name)

    def cascade_to_children(self):
        """
        Child Formulas can reference (my) Parent Attributes, so...
        If the *referenced* Parent Attributes are changed, cascade to child
        Setting update_msg to denote parent_role
        This will cause each child to recompute all formulas referencing that role
        eg,
          OrderDetail.ShippedDate = Order.ShippedDate, so....
          Order cascades changed ShippedDate => OrderDetailList
        """
        referring_children = rule_bank_withdraw.get_referring_children(parent_logic_row=self)
        for each_parent_role_name in referring_children:  # children that reference me
            parent_attributes = referring_children[each_parent_role_name]
            do_cascade = False
            cascading_attribute_name = ""
            for each_parent_attribute in parent_attributes:
                value = getattr(self.row, each_parent_attribute)
                old_value = getattr(self.old_row, each_parent_attribute)
                if value != old_value:
                    do_cascade = True
                    cascading_attribute_name = each_parent_attribute
                    break
            if do_cascade:  # eg, Order cascades ShippedDate => OrderDetailList
                child_role_name = self.get_child_role(each_parent_role_name)
                reason = "Cascading " + each_parent_role_name + \
                         "." + cascading_attribute_name + " (,...)"
                child_rows = getattr(self.row, child_role_name)
                for each_child_row in child_rows:
                    old_child = self.make_copy(each_child_row)
                    each_logic_row = LogicRow(row=each_child_row, old_row=old_child, ins_upd_dlt="upd",
                                              nest_level=1 + self.nest_level,
                                              a_session=self.session, row_sets=self.row_sets)
                    each_logic_row.update(reason=reason)

    def is_parent_cascading(self, parent_role_name: str):
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

    def is_different_parent(self, parent_role_name: str) -> bool:
        """ return True if any changes to foreign key fields of parent_role_name"""
        role_def = self.get_parent_role_def(parent_role_name=parent_role_name)
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

    def is_formula_pruned(self, formula: Formula) -> bool:
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
                    if self.is_different_parent(parent_role_name=role_name):
                        is_parent_changed = True
                        break
                    if self.is_parent_cascading(role_name):
                        is_parent_changed = True
                        break
                else:
                    if getattr(row, column) != getattr(old_row, column):
                        is_dependent_changed = True
                        break
            result_prune = not (is_parent_changed or is_dependent_changed)
        if result_prune:
            self.log("Prune Formula: " + formula._column +
                     " [" + str(formula._dependencies) + "]")
        return result_prune

    def formula_rules(self):
        """ execute un-pruned formulae, in dependency order """
        self.log_engine("formula_rules")
        formula_rules = rule_bank_withdraw.rules_of_class(self, Formula)
        formula_rules.sort(key=lambda formula: formula._exec_order)
        for each_formula in formula_rules:
            if not self.is_formula_pruned(each_formula):
                each_formula.execute(self)

    def constraints(self):
        """ execute constraints (throw error if one fails) """
        # self.log("constraints")
        constraint_rules = rule_bank_withdraw.rules_of_class(self, Constraint)
        for each_constraint in constraint_rules:
            each_constraint.execute(self)

    def load_parents(self):
        """ sqlalchemy lazy does not work for inserts... do it here...
        1. RI would require the sql anyway
        2. Provide a consistent model - your parents are always there for you
            - eg, see add_order event rule - references {sales_rep.Manager.FirstName}
        """
        def is_foreign_key_null(relationship: sqlalchemy.orm.relationships):
            child_columns = relationship.local_columns
            if len(child_columns) == 0:
                raise Exception("Malformed relationship has no foreign key: " +
                                str(relationship))
            for each_child_column in child_columns:
                each_child_column_name = each_child_column.name
                if getattr(self.row, each_child_column_name) is None:
                    return True
            return False

        child_mapper = object_mapper(self.row)
        my_relationships = child_mapper.relationships
        for each_relationship in my_relationships:  # eg, order has parents cust & emp, child orderdetail
            if each_relationship.direction == sqlalchemy.orm.interfaces.MANYTOONE:  # cust, emp
                parent_role_name = each_relationship.key  # eg, OrderList
                if is_foreign_key_null(each_relationship) is False:
                    # continue
                    self.get_parent_logic_row(parent_role_name)  # sets the accessor
                    does_parent_exist = getattr(self.row, parent_role_name)
                    if not does_parent_exist:
                        msg = "Missing Parent: " + parent_role_name
                        self.log(msg)
                        raise Exception(msg)
        return self

    def adjust_parent_aggregates(self):
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
            # print(each_parent_role)
            parent_adjuster = ParentRoleAdjuster(child_logic_row=self,
                                                 parent_role_name=each_parent_role)
            for each_aggregate in each_aggr_list:
                each_aggregate.adjust_parent(parent_adjuster)  # adjusts each_parent iff req'd
            parent_adjuster.save_altered_parents()

    def user_row_update(self, row: base, ins_upd_dlt: str) -> 'LogicRow':
        result_logic_row = LogicRow(row = row,
                                    old_row = self.make_copy(row),
                                    nest_level=self.nest_level+1,
                                    a_session=self.session,
                                    row_sets=self.row_sets,
                                    ins_upd_dlt=ins_upd_dlt)
        return result_logic_row

    def update(self, reason: str = None, row: base = None):
        """
        make updates - with logic - in events, for example

        row = sqlalchemy read
        logic_row.update(row=row, msg="my log message")
        """
        if row is not None:
            user_logic_row = self.user_row_update(row=row, ins_upd_dlt="upd")
            user_logic_row.update(reason=reason)
        else:
            self.reason = reason
            self.log("Update - " + reason)
            self.early_row_events()
            self.copy_rules()
            self.formula_rules()
            self.adjust_parent_aggregates()  # parent chaining (sum / count adjustments)
            self.constraints()
            self.cascade_to_children()  # child chaining (cascade changed parent references)
            if self.row_sets is not None:  # eg, for debug as in upd_order_shipped test
                self.row_sets.remove_submitted(logic_row=self)

    def insert(self, reason: str = None, row: base = None):
        """
        make updates - with logic - in events, for example

        row = sqlalchemy read
        logic_row.update(row=row, msg="my log message")
        """
        if row is not None:
            user_logic_row = self.user_row_update(row=row, ins_upd_dlt="ins")
            user_logic_row.insert(reason=reason)
        else:
            self.reason = reason
            self.log("Insert - " + reason)
            self.load_parents()
            self.early_row_events()
            self.copy_rules()
            self.formula_rules()
            self.adjust_parent_aggregates()
            self.constraints()
            # self.cascade_to_children()

    def delete(self, reason: str = None, row: base = None):
        """
        make updates - with logic - in events, for example

        row = sqlalchemy read
        logic_row.update(row=row, msg="my log message")
        """
        if row is not None:
            user_logic_row = self.user_row_update(row=row, ins_upd_dlt="ins")
            user_logic_row.insert(reason=reason)
        else:
            self.reason = reason
            self.log("delete - " + reason)
            self.early_row_events()
            self.adjust_parent_aggregates()
            self.constraints()
            self.cascade_delete_children()


class ParentRoleAdjuster:
    """
    Contains current / previous parent_logic_row
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

    def save_altered_parents(self):
        """
        Save (chain) parent iff parent_logic_row has been set by sum/count executor.
        This can update parent, and previous parent (ie, foreign key changed)

        Dragons lurk herein
        ===================
            upd_order_reuse changes OrderDetail.ProductId, and Order.CustomerId
            listeners do not guarantee order
            Failures were seen for OrderDetail first
                It adjusted to the New Customer
            Fix is defer adjustment logic iff the parent row is in the submitted list
        """
        if self.parent_logic_row is None:  # save *only altered* parents (often does nothing)
            pass
            # self.child_logic_row.log("adjust not required for parent_logic_row: " + str(self))
        else:
            parent_logic_row = self.parent_logic_row
            if (parent_logic_row.row_sets.is_submitted(parent_logic_row.row)):  # see dragon alert, above
                self.child_logic_row.log("Adjustment deferred for " + self.parent_role_name)
            else:
                parent_logic_row.ins_upd_dlt = "upd"
                parent_logic_row.update(reason="Adjusting " + self.parent_role_name)
                # no after_flush: https://stackoverflow.com/questions/63563680/sqlalchemy-changes-in-before-flush-not-triggering-before-flush
        if self.previous_parent_logic_row is None:
            pass
            # self.child_logic_row.log("save-adjusted not required for previous_parent_logic_row: " + str(self))
        else:
            previous_parent_logic_row = self.previous_parent_logic_row
            if (previous_parent_logic_row.row_sets.is_submitted(previous_parent_logic_row.row)):
                self.child_logic_row.log("Adjustment deferred for " + self.parent_role_name)
            else:
                current_session = self.child_logic_row.session
                previous_parent_logic_row.ins_upd_dlt = "upd"
                previous_parent_logic_row.update(reason="Adjusting " + self.parent_role_name)
