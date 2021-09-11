from sqlalchemy.orm import session
import logic_bank
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.exec_trans_logic.row_sets import RowSets
from logic_bank.rule_bank import rule_bank_withdraw
from logic_bank.rule_type.row_event import CommitRowEvent
from logic_bank.util import get_old_row, prt


def before_commit(a_session: session):
    """
    Unused
        * not called for auto-commit transactions
        * called prior to before_flush
    """
    logic_bank.logic_logger.info(f'\nLogic Phase:\t\tBEFORE COMMIT(session={str(hex(id(a_session)))})          \t\t\t\t\t\t')


def before_flush(a_session: session, a_flush_context, an_instances):
    """
    Logic Execution processes LogicRows: row and old_row

    Note old_row is critical for:
        * user logic (did the value change?  by how much?)
        * performance / pruning (skip rules iff no dependent values change)
        * performance / optimization (1 row adjustments, not expensive select sum/count)
    """

    """
    Logic Phase
    """
    logic_bank.logic_logger.info(f'Logic Phase:\t\tROW LOGIC(session={str(hex(id(a_session)))}) (sqlalchemy before_flush)\t\t\t')

    row_sets = RowSets()  # type : RowSet
    client_inserts = []

    for each_instance in a_session.dirty:
        row_sets.add_submitted(each_instance)

    for each_instance in a_session.new:
        row_sets.add_submitted(each_instance)
        """ inserts first...
            SQLAlchemy queues these on a_session.new (but *not* updates!)
            so, process the client changes, so that triggered inserts (eg. audit) aren't run twice
        """
        client_inserts.append(each_instance)

    bug_explore = None  # None to disable, [None, None] to enable
    if bug_explore is not None:  # temp hack - order rows to explore bug (upd_order_reuse)
        temp_debug(a_session, bug_explore, row_sets)
    else:
        for each_instance in a_session.dirty:
            old_row = get_old_row(each_instance, a_session)
            logic_row = LogicRow(row=each_instance, old_row=old_row, ins_upd_dlt="upd",
                                 nest_level=0, a_session=a_session, row_sets=row_sets)
            logic_row.update(reason="client")

    for each_instance in client_inserts:  # a_session.new:
        logic_row = LogicRow(row=each_instance, old_row=None, ins_upd_dlt="ins",
                             nest_level=0, a_session=a_session, row_sets=row_sets)
        logic_row.insert(reason="client")

    # if len(a_session.deleted) > 0:
        # print("deleting")
    for each_instance in a_session.deleted:
        logic_row = LogicRow(row=each_instance, old_row=None, ins_upd_dlt="dlt",
                             nest_level=0, a_session=a_session, row_sets=row_sets)
        logic_row.delete(reason="client")


    """
    Commit Logic Phase
    """
    logic_bank.logic_logger.info(f'Logic Phase:\t\tCOMMIT(session={str(hex(id(a_session)))})   \t\t\t\t\t\t\t\t\t\t')
    processed_rows = dict.copy(row_sets.processed_rows)  # set in LogicRow ctor
    for each_logic_row_key in processed_rows:
        each_logic_row = processed_rows[each_logic_row_key]
        logic_bank.engine_logger.debug("visit: " + each_logic_row.__str__())
        commit_row_events = rule_bank_withdraw.rules_of_class(each_logic_row, CommitRowEvent)
        for each_row_event in commit_row_events:
            each_logic_row.log("Commit Event")
            each_row_event.execute(each_logic_row)

    """
    Proceed with sqlalchemy flush processing
    """
    logic_bank.logic_logger.info(f'Logic Phase:\t\tFLUSH(session={str(hex(id(a_session)))})   (sqlalchemy flush processing)       \t')


def temp_debug(a_session, bug_explore, row_cache):
    """
    do not delete - see description in nw/tests/upd_order_reuse
    """
    for each_instance in a_session.dirty:
        table_name = each_instance.__tablename__
        if table_name.startswith("OrderDetail"):
            bug_explore[0] = each_instance
        else:
            bug_explore[1] = each_instance
    order_detail_first = False  # true triggers defer
    if order_detail_first:
        each_instance = bug_explore[0]
        old_row = get_old_row(each_instance)
        logic_row = LogicRow(row=each_instance, old_row=old_row, ins_upd_dlt="upd",
                             nest_level=0, a_session=a_session, row_sets=row_cache)
        logic_row.update(reason="client")
        each_instance = bug_explore[1]
        old_row = get_old_row(each_instance)
        logic_row = LogicRow(row=each_instance, old_row=old_row, ins_upd_dlt="upd",
                             nest_level=0, a_session=a_session, row_sets=row_cache)
        logic_row.update(reason="client")
    else:
        each_instance = bug_explore[1]
        old_row = get_old_row(each_instance)
        logic_row = LogicRow(row=each_instance, old_row=old_row, ins_upd_dlt="upd",
                             nest_level=0, a_session=a_session, row_sets=row_cache)
        logic_row.update(reason="client")
        each_instance = bug_explore[0]
        old_row = get_old_row(each_instance)
        logic_row = LogicRow(row=each_instance, old_row=old_row, ins_upd_dlt="upd",
                             nest_level=0, a_session=a_session, row_sets=row_cache)
        logic_row.update(reason="client")
