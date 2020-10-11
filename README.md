Use Logic Bank to govern SQLAlchemy
update transaction logic - multi-table derivations, constraints,
and actions such as sending mail or messages. Logic consists of:

* **Rules - 40X** more concise
using a spreadsheet-like paradigm, and

* **Python - control and extensibility,**
using standard functions and event handlers


Features
--------

Logic Bank is:

- **Extensible:** logic consists of rules (see below), plus standard Python code

- **Multi-table:** rules like `sum` automate complex, multi-table transactions

- **Scalable:** rules are automatically pruned and optimized; for example, sums are processed as *1 row adjustment updates,* rather than expensive SQL aggregate queries

- **Manageable:** develop and debug your rules in IDEs, manage them in SCS systems (such as `git`), using existing procedures


Since transaction logic is nearly half of most database systems,
and rules automate over **95% of the logic 40X more concisely,**
Logic Bank can return meaningful savings in time and cost. 
See the [**Logic Bank Overview**](../../wiki/Home) for more
on the Business Case, and a detailed walk-through.

Skeptical?  You should be.  Choosing an automation
technology ill-suited to transaction processing has
serious implications for performance, quality and manageability.
Unlike familiar rules engines, Logic Bank rules are specifically
designed to be **scalable and extensible**,
and have been **proven in practice** - see
[**Rules Engines**](../../wiki/Rules-Engines).


## Architecture
<figure><img src="images/architecture.png" width="800"></figure>


 1. **Declare** logic as rules and Python (see example below).

 2. Your application makes calls on `SQLAlchemy` for inserts, updates and deletes.

    - By bundling transaction logic into SQLAlchemy data access, your logic
  is automatically shared, whether for hand-written code (Flask apps, APIs)
  or via generators such as Flask AppBuilder.

 3. The **Logic Bank** engine handles SQLAlchemy `before_flush` events on
`Mapped Tables`

 4. The logic engine operates much like a spreadsheet:
    -  **watch** for changes at the attribute level
    -  **react** by running rules that referenced changed attributes,
which can
    - **chain** to still other attributes that refer to
_those_ changes.  Note these might be in different tables,
providing automation for _multi-table logic_.

Logic does not apply to updates outside SQLAlchemy,
nor to SQLAlchemy batch updates or unmapped sql updates.


## Declaring Logic as Spreadsheet-like Rules
To illustrate, let's use an adaption
of the Northwind database,
with a few rollup columns added.
For those not familiar, this is basically
Customers, Orders, OrderDetails and Products,
as shown in the diagrams below.

#### Declare rules using Python
Once you `pip install` LogicBank, logic is declared as spreadsheet-like rules as shown below
from  [`nw/logic/rules_bank.py`](nw/logic/rules_bank.py),
which implements the *check credit* requirement.
This illustrates the advantages of a _declarative_ approach
relative to a legacy _procedural_ approach:

* **Conciseness:** these 5 rules replace [**these 200 lines of legacy code**](../../wiki/by-code).
They are essentially an executable specification: _far_ simpler to understand,
even for business users.

* **Quality:** rules are *automatically reused* all transactions; these
rules governs around a dozen transactions (delete OrderDetail,
change OrderDetail quantity, change OrderDetail Product,
change *both*, etc).

* **Maintainability:** rule execution is *automatically ordered*
per system-discovered dependencies.  So for maintenance,
just change the rules - the system will re-order and re-optimize.

<figure><img src="images/example.png" width="800"></figure>

Note the Python integration:

* Rules are stated in Python, so you get IDE features like type checking,
code completion, source code management, debugging
(the diagram shows a breakpoint in a rule), etc

* Rules are extensible - they can call Python code (see `congratulate_sales_rep`)

This representatively complex transaction illustrates
common logic execution patterns, described below.

#### Activate Rules
To test our rules, we use
[`nw/tests/add_order.py`](nw/tests/add_order.py).
It activates the rules using this import:
```python
from nw.logic import session  # opens db, activates logic listener <--
```
 
This executes [`nw/logic/__init__.py`](nw/logic/__init__.py),
which activates the logic engine:
```python
by_rules = True  # True => use rules, False => use legacy hand code (for comparison)
if by_rules:
    LogicBank.activate(session=session, activator=declare_logic)
else:
    # ... conventional after_flush listeners (to see rules/code contrast)
```

Let's see how logic operates.

## Logic Execution: Add Order - Watch, React, Chain

<figure><img src="images/check-credit.png" width="500"></figure>


The `add_order` example illustrates how
__Watch / React / Chain__ operates to
check the Credit Limit:

1. The `OrderDetail.UnitPrice` is referenced from the Product,
so it is copied

1. OrderDetails are referenced by the Orders' `AmountTotal` sum rule,
so `AmountTotal` is adjusted

    * Multi-table logic is **scalable** - this rule executes as a 1-row
    *adjustment* update, not an expensive `select sum`

1. The `AmountTotal` is referenced by the Customers' `Balance`,
so it is adjusted

1. And the Credit Limit constraint is checked 
(exceptions are raised if constraints are violated,
and the transaction is rolled back)

All of the dependency management to see which attribute have changed,
logic ordering, the SQL commands to read and adjust rows, and the chaining
are fully automated by the engine, based solely on the rules above.
See the [detail walk-through here](../../wiki#example-add-order---multi-table-adjustment-chaining).

**Reuse over Use Cases is automatic,** so the same rules
automate deleting and updating orders.
This is how 5 rules represent the same logic as 200 lines of code.

To see more on how __watch__, __react__ and __chain__ 
logic automates and optimizes multi-table transactions,
[click here](../../wiki/Rules-Engines#multi-table-logic-execution).


## An Agile Perspective
The core tenant of agile is _working software,_
driving _collaboration,_ for _rapid iterations._
Here's how rules can help.

#### Working Software _Now_
The examples above illustrate how just a few rules can replace 
[pages of code](../../wiki/by-code).

#### Collaboration: Running Screens - Automatic Basic Web App

Certainly business users are more easily able to
read rules than code.  But still, rules are
pretty abstract.

Business users relate best to actual working pages -
_their_ interpretation of working software.
The [fab-quick-start](https://github.com/valhuber/fab-quick-start/wiki)
project enables you to build a basic web app in minutes.


<figure><img src="images/fab.png" width="800"></figure>

This project has already generated such an app, which you can run like this
once you've finished the Installation process, below.

#### Iteration - Automatic Ordering
Rules are _self-ordering_ - they recognize their interdependencies,
and order their execution and database access (pruning, adjustments etc)
accordingly.  This means:

* order is independent - you can state the rules in any order
and get the same result

* maintenance is simple - just make changes, additions and deletions,
the engine will reorganize execution order and database access, automatically


## Installation
### Verify Pre-reqs: Python 3.8, virtualenv, pip3
Ensure you have these pre-reqs
```
python --version
# requires 3.8 or higher

pip --version
# version 19.2.3 or higher... you might be using pip3

pyenv --version
# 1.2.19 or higher
```

If you are missing any, install them as [described here](../../wiki/Explore-Logic-Bank).
We also recommend an IDE such as PyCharm, VSCode, etc.

### Install Logic-Bank
In your IDE or Command Line:

```
# optionally fork, and then
git clone https://github.com/valhuber/Logic-Bank.git
cd Logic-Bank
virtualenv venv
# windows: .\venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
```

#### Verify and Run

##### Run `basic_web_app`

```
cd Logic-Bank
cd nw/basic_web_app
# windows set FLASK_APP=app
export FLASK_APP=app
flask run
```
You then start the app (use **new window**) with [`http://127.0.0.1:5000/`]( http://127.0.0.1:5000/)
> **Login** (upper right): user = admin, password = p

You can
1. Navigate to Order 11011 (a _multi-page_ web app)
    * Click **Menu > Customer List** 
    * Click the **magnifying glass** for the first customer
    * Click the **List Order tab**
    * Click the **magnifying glass* for Order **11011**
2. Click Edit so you can make changes
3. Change the Shipped Date
4. Click save
5. Verify logic enforcement
    * The web app has been [configured](../../wiki/Flask-App-Builder-Integration) to activate the rules
    * The logic for this update [is interesting](../../wiki/home#example-ship-order---pruning-adjustment-and-cascade) -
    check out the console log

##### Run the `nw/tests`
Run the `nw/tests` programs under your IDE or the
command line; start with `add_order` and `upd_order_shipped,`
and see the [walk-throughs here](../../wiki/home).
 - Note: the **log** depicts logic execution

#### What's in the project
Logic Bank consists of:

* Two test database systems - `nw` and `banking`;
these both contain

    * [Databases](nw/db) sqlite - no install required

    * [Test folders](nw/tests) than run key transactions - just run the scripts
(note the logs)

    * [Flask AppBuilder apps](nw/basic_web_app) (as described above)
    
    * [Logic](nw/logic) - models and rules (and for `nw`,
    the manual `legacy` code for contrast to rules)
    
* The `nw` sample illustrates comparisons of Business logic, both
[by code](../../wiki/by-code) and by rules (shown above).

* The `logic_bank` engine source code

To explore:

* Click [here](../../wiki/Explore-Logic-Bank)
    for install / operations procedures
    
* Click [here](../../wiki/Logic-Walkthrough) for a
    short overview of internal logic execution

##### See also the Logic-Bank-Examples project
The `Logic Bank Examples` [here](../../wiki/Sample-Project---Setup)
contains the same examples, but _not_ the `logic_bank` engine source code.
It uses the logic engine via `pip install`, as you would for your own projects:

```
pip install -i https://test.pypi.org/simple/ logic-bank
```
> This is **not required here**, and requires the same
> pre-reqs noted above

#### Status: Running, Under Development
Functionally complete, 9/29/2020, tested for 2 databases.

Incubation - ready to explore and provide feedback
on general value, and features.
