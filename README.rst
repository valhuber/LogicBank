Python Rules - Logic for SQLAlchemy
===================================

This package enables you to declare rules that govern SQLAlchemy
update transaction logic (multi-table derivations, constraints,
and actions such as sending mail or messages).

Logic is stated in Python, and is over an **40X
more concise than code.**


Features
--------

Logic is declared in Python (example below), and is:

- **Extensible:** logic consists of rules (see below), plus standard Python code

- **Multi-table:** rules like `sum` automate multi-table transactions

- **Scalable:** rules are pruned and optimized; for example, sums are processed as *1 row adjustment updates,* rather than expensive SQL aggregate queries

- **Manageable:** develop and debug your rules in IDEs, manage it in SCS systems (such as `git`) using existing procedures


Example:
--------
The following 5 rules represent the same logic as 200 lines
of Python:

.. code-block:: Python

    def activate_basic_check_credit_rules():
        """ Check Credit Requirement:
            * the balance must not exceed the credit limit,
            * where the balance is the sum of the unshipped order totals
            * which is the rollup of OrderDetail Price * Quantities:
        """

        Rule.constraint(validate=Customer, as_condition=lambda row: row.Balance <= row.CreditLimit,
                        error_msg="balance ({row.Balance}) exceeds credit ({row.CreditLimit})")
        Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountTotal,
                 where=lambda row: row.ShippedDate is None)  # *not* a sql select sum

        Rule.sum(derive=Order.AmountTotal, as_sum_of=OrderDetail.Amount)

        Rule.formula(derive=OrderDetail.Amount, as_expression=lambda row: row.UnitPrice * row.Quantity)
        Rule.copy(derive=OrderDetail.UnitPrice, from_parent=Product.UnitPrice)


To activate the rules declared above:

.. code-block:: Python

    rule_bank_setup.setup(session, engine)
    activate_basic_check_credit_rules()
    rule_bank_setup.validate(session, engine)  # checks for cycles, etc

Depends on:
-----------
- SQLAlchemy
- Python 3.8


More information:
-----------------
See the `logic-bank github <https://github.com/valhuber/logic-bank/wiki>`_
for more information, and explore the code.


Acknowledgements
----------------
Many thanks to

- Tyler Band, for early testing



Change Log
----------

0.0.1 - Initial Version
