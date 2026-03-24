from domain.models import ExpenseDraft, PaymentDraft


EXPENSE_DRAFT_KEY = "expense_draft"
PAYMENT_DRAFT_KEY = "payment_draft"


def create_expense_draft(context) -> ExpenseDraft:
    draft = ExpenseDraft()
    context.user_data.clear()
    context.user_data[EXPENSE_DRAFT_KEY] = draft
    return draft


def get_expense_draft(context) -> ExpenseDraft:
    draft = context.user_data.get(EXPENSE_DRAFT_KEY)
    if draft is None:
        draft = ExpenseDraft()
        context.user_data[EXPENSE_DRAFT_KEY] = draft
    return draft


def create_payment_draft(context) -> PaymentDraft:
    draft = PaymentDraft()
    context.user_data.clear()
    context.user_data[PAYMENT_DRAFT_KEY] = draft
    return draft


def get_payment_draft(context) -> PaymentDraft:
    draft = context.user_data.get(PAYMENT_DRAFT_KEY)
    if draft is None:
        draft = PaymentDraft()
        context.user_data[PAYMENT_DRAFT_KEY] = draft
    return draft
