"""Red-flag categories tuned for Indian annual reports (Ind AS, Companies Act 2013, SEBI LODR)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    description: str
    queries: list
    keywords: list


CATEGORIES = [
    Category(
        id="auditor",
        label="Auditor qualifications & audit-report remarks",
        description=(
            "Qualified, adverse or disclaimer opinions; emphasis of matter; material uncertainty on going "
            "concern; adverse CARO 2020 remarks; internal financial controls weaknesses; accounting software "
            "without audit trail; auditor resignation."
        ),
        queries=[
            "auditor's report qualified opinion adverse opinion disclaimer of opinion",
            "emphasis of matter material uncertainty related to going concern",
            "key audit matters",
            "CARO 2020 report qualifications reservations adverse remarks",
            "internal financial controls over financial reporting material weakness",
            "accounting software audit trail feature not operated",
        ],
        keywords=[
            "qualified opinion", "adverse opinion", "disclaimer of opinion", "emphasis of matter",
            "going concern", "material uncertainty", "key audit matter", "caro",
            "internal financial controls", "audit trail", "material weakness", "except for",
            "resignation of auditor",
        ],
    ),
    Category(
        id="rpt",
        label="Related-party transactions",
        description=(
            "Large or unusual transactions, loans or advances with promoters, directors, subsidiaries or "
            "group entities; transactions not at arm's length or outside the ordinary course of business."
        ),
        queries=[
            "related party transactions Ind AS 24 disclosure",
            "loans and advances to promoter group entities related parties",
            "related party transactions not in ordinary course or not at arm's length",
            "material related party transactions SEBI LODR Regulation 23",
        ],
        keywords=[
            "related party", "promoter group", "key managerial personnel", "arm's length",
            "ordinary course of business", "loans to", "advances to", "regulation 23",
            "ind as 24", "enterprises over which",
        ],
    ),
    Category(
        id="contingent",
        label="Contingent liabilities & litigation",
        description=(
            "Claims not acknowledged as debt, disputed tax or GST demands, guarantees given, pending "
            "litigation, show-cause notices or regulatory proceedings."
        ),
        queries=[
            "contingent liabilities and commitments claims not acknowledged as debt",
            "disputed income tax GST demand under appeal",
            "pending litigation show cause notice regulatory proceedings",
            "corporate guarantees given on behalf of subsidiaries or others",
        ],
        keywords=[
            "contingent liabilit", "not acknowledged as debt", "disputed", "show cause", "appeal",
            "demand", "guarantee", "litigation", "enforcement directorate", "sebi order",
            "penalty", "ind as 37",
        ],
    ),
    Category(
        id="accounting",
        label="Accounting policy / estimate changes & restatements",
        description=(
            "Changes in accounting policy or estimates (useful lives, revenue recognition), restatement of "
            "prior-year numbers, prior-period errors, reclassification of comparatives."
        ),
        queries=[
            "change in accounting policy",
            "change in accounting estimate useful life depreciation",
            "restatement of previous year figures prior period errors",
            "reclassification regrouping of comparative figures",
            "change in revenue recognition policy",
        ],
        keywords=[
            "change in accounting policy", "change in accounting estimate", "restated", "restatement",
            "prior period", "reclassified", "regrouped", "useful life", "ind as 8",
            "revised estimate", "retrospective",
        ],
    ),
    Category(
        id="unusual",
        label="Unusual notes to accounts",
        description=(
            "Exceptional items, impairments and write-offs, rising doubtful receivables, defaults or delays "
            "in statutory dues, stalled capital work-in-progress, loans to directors, fraud reporting."
        ),
        queries=[
            "exceptional items and one-time write-offs impairment",
            "expected credit loss provision trade receivables overdue doubtful",
            "delay in payment of statutory dues default in repayment of borrowings",
            "capital work in progress ageing and capitalisation",
            "loans given to directors or entities in which directors are interested",
            "fraud reported by auditors under section 143(12) whistle blower",
        ],
        keywords=[
            "exceptional item", "impairment", "write off", "written off", "doubtful",
            "expected credit loss", "default", "overdue", "statutory dues", "capital work",
            "section 143(12)", "fraud", "whistle", "revaluation", "unhedged",
        ],
    ),
    Category(
        id="governance",
        label="Governance & liquidity stress",
        description=(
            "Promoter share pledges, abrupt resignations of directors/CFO/auditor, credit-rating downgrades, "
            "secretarial-audit remarks, exchange penalties, debt restructuring or one-time settlements."
        ),
        queries=[
            "pledge of promoter shares encumbrance",
            "resignation of director chief financial officer company secretary or statutory auditor",
            "credit rating downgrade",
            "qualification or adverse remark in secretarial audit report",
            "penalty or fine imposed by stock exchange for non-compliance",
        ],
        keywords=[
            "pledge", "encumbrance", "resign", "credit rating", "downgrade", "secretarial audit",
            "non-compliance", "penalty", "fine imposed", "one time settlement", "restructuring",
            "moratorium",
        ],
    ),
]

CATEGORY_BY_ID = {c.id: c for c in CATEGORIES}

# Used to pull the numbers needed for ratio analysis
METRIC_QUERIES = [
    "statement of profit and loss revenue from operations total income profit before tax profit after tax finance costs",
    "balance sheet total equity borrowings non-current current",
    "current assets trade receivables inventories current liabilities",
    "statement of cash flows net cash generated from operating activities",
]
METRIC_KEYWORDS = [
    "revenue from operations", "profit before tax", "finance costs", "total equity", "borrowings",
    "trade receivables", "inventories", "net cash", "operating activities",
    "total current assets", "total current liabilities",
]
