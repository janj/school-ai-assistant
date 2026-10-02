"""Metadata for the admin data editor (Track D builds generic CRUD + forms from this).

Every editable table is center-scoped. `center_slug` and `id` are never editable;
the editor fills center_slug from the admin's session.

Column types: text | longtext | markdown | time | date | int | money_cents | key

`key` columns are the stable placeholder keys (Phase 3.0): required on create, lowercase
letters/digits/underscores, unique per center, and read-only after creation.
"""

EDITABLE = {
    "centers": {
        "label": "Center info",
        "single_row": True,  # the admin's own center row only; keyed by slug, no create/delete
        "order_by": "slug",
        "columns": [
            ("name", "text", "Name", True),
            ("tagline", "text", "Tagline", False),
            ("address", "text", "Address", False),
            ("main_phone", "text", "Main phone", True),
            ("main_email", "text", "Main email", True),
            ("website", "text", "Website", False),
        ],
    },
    "contacts": {
        "label": "Directory",
        "order_by": "sort_order, name",
        "columns": [
            ("key", "key", "Key", True),
            ("name", "text", "Name", True),
            ("position", "text", "Position", True),
            ("phone", "text", "Phone", False),
            ("email", "text", "Email", False),
            ("sort_order", "int", "Sort order", False),
        ],
    },
    "hours": {
        "label": "Hours of operation",
        "order_by": "id",
        "columns": [
            ("key", "key", "Key", True),
            ("days", "text", "Days", True),
            ("open_time", "time", "Opens", False),
            ("close_time", "time", "Closes", False),
            ("notes", "text", "Notes", False),
        ],
    },
    "closures": {
        "label": "Closure dates",
        "order_by": "start_date",
        "columns": [
            ("start_date", "date", "Start date", True),
            ("end_date", "date", "End date", False),
            ("name", "text", "Name", True),
            ("notes", "text", "Notes", False),
        ],
    },
    "schedule_blocks": {
        "label": "Daily schedule",
        "order_by": "age_group, start_time",
        "columns": [
            ("age_group", "text", "Age group", True),
            ("start_time", "time", "Start", True),
            ("end_time", "time", "End", False),
            ("activity", "text", "Activity", True),
        ],
    },
    "fees": {
        "label": "Fees",
        "order_by": "category, name",
        "columns": [
            ("key", "key", "Key", True),
            ("category", "text", "Category", True),
            ("name", "text", "Name", True),
            ("amount_cents", "money_cents", "Amount", False),
            ("period", "text", "Period", False),
            ("notes", "longtext", "Notes", False),
        ],
    },
    "lunch_menu": {
        "label": "Lunch menu",
        "order_by": "id",
        "columns": [
            ("day", "text", "Day", True),
            ("meal", "text", "Meal", True),
            ("items", "longtext", "Items", True),
            ("notes", "text", "Notes", False),
        ],
    },
    "facts": {
        "label": "Facts",
        "order_by": "key",
        "columns": [
            ("key", "key", "Key", True),
            ("label", "text", "Label", True),
            ("value", "text", "Value", True),
            ("notes", "text", "Notes", False),
        ],
    },
    "policies": {
        "label": "Policies",
        "order_by": "topic",
        "columns": [
            ("topic", "text", "Topic slug", True),
            ("title", "text", "Title", True),
            ("body_md", "markdown", "Body", True),
        ],
    },
    "faq": {
        "label": "Admin answers (FAQ)",
        "order_by": "created_at DESC",
        "columns": [
            ("question", "longtext", "Question", True),
            ("answer", "longtext", "Answer", True),
        ],
    },
}
