from sqlalchemy.orm import session
import logic_bank
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.exec_trans_logic.row_sets import RowSets
from logic_bank.rule_bank import rule_bank_withdraw
from logic_bank.rule_type.row_event import CommitRowEvent, AfterFlushRowEvent
from logic_bank.util import get_old_row, prt


def before_commit(a_session: session):
    """
    Unused
        * not called for auto-commit transactions
        * called prior to before_flush
    """
    # logic_bank.logic_logger.debug(f'\nLogic Phase:\t\tBEFORE COMMIT(session={str(hex(id(a_session)))})          \t\t\t\t\t\t')


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
    updates = 0
    inserts = 0
    deletes = 0
    if 'processed_rows' in a_session.info:
        logic_bank.logic_logger.debug(f'Logic Phase:\t\tROW LOGIC IGNORE RE-RAISE(session={str(hex(id(a_session)))}) (sqlalchemy before_flush)\t\t\t')
        a_session.info.pop('processed_rows')
        a_session.info.pop('row_sets')
        # return
    
    logic_bank.logic_logger.info(f'\nLogic Phase:\t\tROW LOGIC\t\t(session={str(hex(id(a_session)))}) (sqlalchemy before_flush)\t\t\t')

    row_sets = RowSets()  # type : RowSet

    for each_instance in a_session.dirty:
        row_sets.add_submitted(each_instance)

    for each_instance in a_session.new:
        row_sets.add_submitted(each_instance)
        row_sets.add_client_inserts(each_instance)

    """ updates first, inserts second...
        SQLAlchemy queues these on a_session.new (but *not* updates!)
        so, process the client changes, so that triggered inserts (eg. audit) aren't run twice
    """
    bug_explore = None  # None to disable, [None, None] to enable
    if bug_explore is not None:  # temp hack - order rows to explore bug (upd_order_reuse)
        temp_debug(a_session, bug_explore, row_sets)
    else:
        for each_instance in a_session.dirty:
            old_row = get_old_row(each_instance, a_session)
            logic_row = LogicRow(row=each_instance, old_row=old_row, ins_upd_dlt="upd",
                                 nest_level=0, a_session=a_session, row_sets=row_sets)
            updates += 1
            logic_row.update(reason="client")

    for each_instance in row_sets.client_inserts:  # a_session.new:
        logic_row = LogicRow(row=each_instance, old_row=None, ins_upd_dlt="ins",
                             nest_level=0, a_session=a_session, row_sets=row_sets)
        inserts += 1
        logic_row.insert(reason="client")

    # if len(a_session.deleted) > 0:
        # print("deleting")
    do_not_adjust_list = []
    for each_instance in a_session.deleted:
        logic_row = LogicRow(row=each_instance, old_row=None, ins_upd_dlt="dlt",
                             nest_level=0, a_session=a_session, row_sets=row_sets)
        deletes += 1
        logic_row.delete(reason="client", do_not_adjust_list = do_not_adjust_list)
        do_not_adjust_list.append(logic_row)


    """
    Commit Logic Phase
    """
    logic_bank.logic_logger.info(f'Logic Phase:\t\tCOMMIT LOGIC\t\t(session={str(hex(id(a_session)))})   \t\t\t\t\t\t\t\t\t\t')
    processed_rows = dict.copy(row_sets.processed_logic_rows)  # set in LogicRow ctor
    for each_logic_row_key in processed_rows:
        each_logic_row : LogicRow = processed_rows[each_logic_row_key]
        logic_bank.engine_logger.debug("visit: " + each_logic_row.__str__())
        commit_row_events = rule_bank_withdraw.rules_of_class(each_logic_row, CommitRowEvent)
        for each_row_event in commit_row_events:
            each_logic_row.log("Commit Event")
            each_row_event.execute(each_logic_row)

    a_session.info['processed_rows'] = dict.copy(row_sets.processed_logic_rows)  # for after_flush
    a_session.info['row_sets'] = row_sets

    """
    After_flush Logic Phase
    """
def after_flush(a_session: session, a_flush_context):   #, an_instances):
    logic_bank.logic_logger.info(f'Logic Phase:\t\tAFTER_FLUSH LOGIC\t(session={str(hex(id(a_session)))})   \t\t\t\t\t\t\t\t\t\t')

    processed_rows = {}
    row_sets = RowSets()
    if 'processed_rows' in a_session.info:
        processed_rows = a_session.info['processed_rows']
        row_sets = a_session.info['row_sets']

    for each_logic_row_key in processed_rows:
        each_logic_row = processed_rows[each_logic_row_key] # type: LogicRow
        each_logic_row.log_engine("after_flush")
        after_flush_row_events = rule_bank_withdraw.rules_of_class(each_logic_row, AfterFlushRowEvent)
        for each_row_event in after_flush_row_events:
            each_logic_row.log("AfterFlush Event")
            each_row_event.execute(each_logic_row)

    use_session_lists = False
    if use_session_lists:
        # if len(a_session.deleted) > 0:
            # print("deleting")
        row_sets = RowSets()  # type : RowSet

        for each_instance in a_session.dirty:
            row_sets.add_submitted(each_instance)

        for each_instance in a_session.new:
            row_sets.add_submitted(each_instance)
            row_sets.add_client_inserts(each_instance)

        do_not_adjust_list = []
        for each_instance in a_session.deleted:
            logic_row = LogicRow(row=each_instance, old_row=None, ins_upd_dlt="dlt",
                                 nest_level=0, a_session=a_session, row_sets=row_sets)
            logic_row.delete(reason="client", do_not_adjust_list = do_not_adjust_list)
            do_not_adjust_list.append(logic_row)

        processed_rows = dict.copy(row_sets.processed_logic_rows)  # set in LogicRow ctor
        for each_instance in row_sets.client_inserts:
            each_logic_row = LogicRow(row=each_instance, old_row=None, ins_upd_dlt="ins",
                                 nest_level=0, a_session=a_session, row_sets=row_sets)
            # each_logic_row = processed_rows[each_logic_row_key]
            # logic_bank.engine_logger.log("after_flush visits: ", each_logic_row.__str__())  # FIXME
            each_logic_row.log("after_flush visits")
            commit_row_events = rule_bank_withdraw.rules_of_class(each_logic_row, AfterFlushRowEvent)
            for each_row_event in commit_row_events:
                each_logic_row.log("after_flush Commit Event (BYPASSED)")
                pass
                # each_row_event.execute(each_logic_row)
        row_sets.print_used()
    row_sets.print_used()
    logic_bank.logic_logger.info(f'\nLogic Phase:\t\tCOMPLETE(session={str(hex(id(a_session)))}))       \t')

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
