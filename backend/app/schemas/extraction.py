from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.document import FieldValue


# ==========================================
# 1. Invoice Structured Schemas
# ==========================================
class InvoiceLineItem(BaseModel):
    item_number: Optional[int] = None
    description: str
    quantity: float
    unit_of_measure: Optional[str] = None
    unit_price: float
    amount: float  # Net amount
    tax_rate: Optional[float] = None  # e.g., 10% -> 0.10
    tax_amount: Optional[float] = None
    gross_amount: Optional[float] = None


class InvoiceData(BaseModel):
    invoice_number: FieldValue
    invoice_date: FieldValue
    vendor_name: FieldValue
    customer_name: FieldValue
    currency: FieldValue
    subtotal: FieldValue
    tax_amount: FieldValue
    discount: FieldValue
    total_amount: FieldValue
    cash_paid: Optional[FieldValue] = None
    change: Optional[FieldValue] = None
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    additional_fields: Dict[str, Any] = Field(default_factory=dict)


# ==========================================
# 2. Balance Sheet Schemas
# ==========================================
class BalanceSheetLineItem(BaseModel):
    category: str  # "capital_and_liabilities" or "assets"
    item_name: str
    schedule: Optional[str] = None
    values_by_period: Dict[str, float] = Field(default_factory=dict)


class BalanceSheetData(BaseModel):
    statement_title: FieldValue
    company_name: FieldValue
    currency: FieldValue
    unit: FieldValue  # e.g. "in '000" or "in crore"
    periods: List[str] = Field(default_factory=list)
    total_assets: Dict[str, FieldValue] = Field(default_factory=dict)
    total_capital_and_liabilities: Dict[str, FieldValue] = Field(default_factory=dict)
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    additional_fields: Dict[str, Any] = Field(default_factory=dict)


# ==========================================
# 3. Profit & Loss Schemas
# ==========================================
class ProfitLossLineItem(BaseModel):
    section: str  # "income", "expenditure", "profit", "appropriations"
    item_name: str
    schedule: Optional[str] = None
    values_by_period: Dict[str, float] = Field(default_factory=dict)


class ProfitLossData(BaseModel):
    statement_title: FieldValue
    company_name: FieldValue
    currency: FieldValue
    unit: FieldValue
    periods: List[str] = Field(default_factory=list)
    # Income
    interest_earned: Dict[str, FieldValue] = Field(default_factory=dict)
    other_income: Dict[str, FieldValue] = Field(default_factory=dict)
    total_income: Dict[str, FieldValue] = Field(default_factory=dict)
    # Expenditure
    interest_expended: Dict[str, FieldValue] = Field(default_factory=dict)
    operating_expenses: Dict[str, FieldValue] = Field(default_factory=dict)
    provisions_and_contingencies: Dict[str, FieldValue] = Field(default_factory=dict)
    total_expenditure: Dict[str, FieldValue] = Field(default_factory=dict)
    # Profits & Appropriations
    net_profit_for_year: Dict[str, FieldValue] = Field(default_factory=dict)
    minority_interest: Dict[str, FieldValue] = Field(default_factory=dict)
    share_in_associates: Dict[str, FieldValue] = Field(default_factory=dict)
    consolidated_net_profit_group: Dict[str, FieldValue] = Field(default_factory=dict)
    balance_brought_forward: Dict[str, FieldValue] = Field(default_factory=dict)
    amalgamation_impact: Dict[str, FieldValue] = Field(default_factory=dict)
    total_appropriations: Dict[str, FieldValue] = Field(default_factory=dict)
    line_items: List[Dict[str, Any]] = Field(default_factory=list)


# ==========================================
# 4. Cash Flow Schemas
# ==========================================
class CashFlowLineItem(BaseModel):
    activity: str  # "operating", "investing", "financing", "reconciliation"
    item_name: str
    values_by_period: Dict[str, float] = Field(default_factory=dict)


class CashFlowData(BaseModel):
    statement_title: FieldValue
    company_name: FieldValue
    currency: FieldValue
    unit: FieldValue
    periods: List[str] = Field(default_factory=list)
    operating_cash_flow: Dict[str, FieldValue] = Field(default_factory=dict)
    investing_cash_flow: Dict[str, FieldValue] = Field(default_factory=dict)
    financing_cash_flow: Dict[str, FieldValue] = Field(default_factory=dict)
    fx_translation_adjustment: Dict[str, FieldValue] = Field(default_factory=dict)
    net_increase_in_cash: Dict[str, FieldValue] = Field(default_factory=dict)
    opening_cash: Dict[str, FieldValue] = Field(default_factory=dict)
    amalgamation_cash: Dict[str, FieldValue] = Field(default_factory=dict)
    closing_cash: Dict[str, FieldValue] = Field(default_factory=dict)
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
