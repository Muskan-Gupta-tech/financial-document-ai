from typing import Dict, Any, List
from backend.app.schemas.document import ValidationCheck, ValidationBlock
from backend.app.utils.number_utils import (
    parse_financial_number,
    approx_equal,
    calculate_variance,
)
from backend.app.core.config import settings
from backend.app.core.logging import logger


class FinancialValidationService:
    def __init__(self, tolerance: float = None):
        self.tolerance = tolerance if tolerance is not None else settings.FINANCIAL_TOLERANCE
        self.large_tolerance = settings.ROUNDING_TOLERANCE_LARGE

    def validate(self, document_type: str, extracted_data: Dict[str, Any]) -> ValidationBlock:
        """Dispatches to the specific validation rules for the given document type."""
        doc_type = document_type.lower().strip()
        checks: List[ValidationCheck] = []
        issues: List[str] = []

        if doc_type == "invoice":
            checks = self._validate_invoice(extracted_data)
        elif doc_type == "balance_sheet":
            checks = self._validate_balance_sheet(extracted_data)
        elif doc_type in ("profit_and_loss", "profit_loss"):
            checks = self._validate_profit_and_loss(extracted_data)
        elif doc_type in ("cash_flow_statement", "cash_flow"):
            checks = self._validate_cash_flow(extracted_data)
        else:
            logger.warning(f"Unknown document type for validation: {document_type}")

        # Determine overall status and collect issues
        has_failure = False
        for c in checks:
            if c.status == "FAIL":
                has_failure = True
                issues.append(f"Validation failed for '{c.name}': {c.notes or 'Variance exceeded tolerance'}")

        overall_status = "FAIL" if has_failure else "PASS"
        return ValidationBlock(checks=checks, overall_status=overall_status, issues=issues)

    # -------------------------------------------------------------------------
    # 1. Invoice Validations
    # -------------------------------------------------------------------------
    def _validate_invoice(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []

        # Helper to safely extract float value from FieldValue or direct scalar
        def get_val(key: str):
            obj = data.get(key)
            if isinstance(obj, dict):
                return parse_financial_number(obj.get("value"))
            return parse_financial_number(obj)

        subtotal = get_val("subtotal")
        tax_amount = get_val("tax_amount") or 0.0
        discount = get_val("discount") or 0.0
        total_amount = get_val("total_amount")
        cash_paid = get_val("cash_paid")
        change = get_val("change")

        # 1.1 Line Items: Quantity * Unit Price ≈ Line Total
        line_items = data.get("line_items", [])
        if line_items and isinstance(line_items, list):
            line_check_failures = []
            sum_line_totals = 0.0
            for idx, item in enumerate(line_items):
                qty = parse_financial_number(item.get("quantity"))
                price = parse_financial_number(item.get("unit_price"))
                amt = parse_financial_number(item.get("amount") or item.get("line_total"))
                if qty is not None and price is not None and amt is not None:
                    calc_line = round(qty * price, 2)
                    sum_line_totals += amt
                    if not approx_equal(calc_line, amt, tolerance=self.tolerance):
                        line_check_failures.append(
                            f"Item #{idx+1}: {qty} * {price} = {calc_line} != {amt}"
                        )
                elif amt is not None:
                    sum_line_totals += amt

            line_status = "FAIL" if line_check_failures else "PASS"
            checks.append(
                ValidationCheck(
                    name="invoice_line_items_arithmetic",
                    formula="quantity * unit_price == line_total",
                    operands={"total_items_checked": len(line_items), "failures": line_check_failures},
                    calculated_value=None,
                    reported_value=None,
                    variance=0.0 if not line_check_failures else float(len(line_check_failures)),
                    status=line_status,
                    notes="All line item unit price multiplications reconciled." if not line_check_failures else "; ".join(line_check_failures),
                )
            )

            # 1.2 Sum of line totals reconcile to subtotal / total
            target_sum = subtotal if subtotal is not None else total_amount
            if target_sum is not None:
                calc_sum = round(sum_line_totals, 2)
                var = calculate_variance(calc_sum, target_sum)
                is_ok = approx_equal(calc_sum, target_sum, tolerance=self.tolerance)
                checks.append(
                    ValidationCheck(
                        name="invoice_line_items_sum_reconciliation",
                        formula="sum(line_totals) == subtotal",
                        operands={"sum_of_lines": calc_sum, "reported_subtotal_or_total": target_sum},
                        calculated_value=calc_sum,
                        reported_value=target_sum,
                        variance=var,
                        status="PASS" if is_ok else "FAIL",
                        notes="Sum of line items matches reported subtotal." if is_ok else f"Variance of {var}",
                    )
                )

        # 1.3 Invoice Total Check: subtotal + tax_amount - discount == total_amount
        if subtotal is not None and total_amount is not None:
            calc_total = round(subtotal + tax_amount - discount, 2)
            var = calculate_variance(calc_total, total_amount)
            is_ok = approx_equal(calc_total, total_amount, tolerance=self.tolerance)
            # Check if tax was already included in subtotal
            if not is_ok and approx_equal(subtotal - discount, total_amount, tolerance=self.tolerance):
                is_ok = True
                calc_total = round(subtotal - discount, 2)
                var = 0.0

            checks.append(
                ValidationCheck(
                    name="invoice_total_check",
                    formula="subtotal + tax_amount - discount",
                    operands={"subtotal": subtotal, "tax_amount": tax_amount, "discount": discount},
                    calculated_value=calc_total,
                    reported_value=total_amount,
                    variance=var,
                    status="PASS" if is_ok else "FAIL",
                    notes="Invoice total mathematically verified." if is_ok else f"Expected {calc_total}, got {total_amount}",
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    name="invoice_total_check",
                    formula="subtotal + tax_amount - discount",
                    operands={"subtotal": subtotal, "tax_amount": tax_amount, "discount": discount},
                    calculated_value=None,
                    reported_value=total_amount,
                    variance=None,
                    status="NOT_APPLICABLE",
                    notes="Required fields (subtotal or total_amount) not present in document",
                )
            )

        # 1.4 Cash and change check (if available)
        if cash_paid is not None and change is not None and total_amount is not None:
            calc_change = round(cash_paid - total_amount, 2)
            var = calculate_variance(calc_change, change)
            is_ok = approx_equal(calc_change, change, tolerance=self.tolerance)
            checks.append(
                ValidationCheck(
                    name="invoice_cash_change_check",
                    formula="cash_paid - total_amount == change",
                    operands={"cash_paid": cash_paid, "total_amount": total_amount},
                    calculated_value=calc_change,
                    reported_value=change,
                    variance=var,
                    status="PASS" if is_ok else "FAIL",
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    name="invoice_cash_change_check",
                    formula="cash_paid - total_amount == change",
                    operands={},
                    status="NOT_APPLICABLE",
                    notes="Cash paid or change not present in document",
                )
            )

        return checks

    # -------------------------------------------------------------------------
    # 2. Balance Sheet Validations
    # -------------------------------------------------------------------------
    def _validate_balance_sheet(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        periods = data.get("periods", [])
        if not periods:
            periods = ["default"]

        total_assets_dict = data.get("total_assets", {})
        total_cap_dict = data.get("total_capital_and_liabilities", {})
        line_items = data.get("line_items", [])

        for p in periods:
            # 2.1 Total Capital & Liabilities ≈ Total Assets
            cap_val_obj = total_cap_dict.get(p, {})
            asset_val_obj = total_assets_dict.get(p, {})

            cap_val = parse_financial_number(cap_val_obj.get("value") if isinstance(cap_val_obj, dict) else cap_val_obj)
            asset_val = parse_financial_number(asset_val_obj.get("value") if isinstance(asset_val_obj, dict) else asset_val_obj)

            if cap_val is not None and asset_val is not None:
                var = calculate_variance(cap_val, asset_val)
                is_ok = approx_equal(cap_val, asset_val, tolerance=self.large_tolerance)
                checks.append(
                    ValidationCheck(
                        name=f"balance_sheet_equation_{p}",
                        formula="total_capital_and_liabilities == total_assets",
                        operands={"total_capital_and_liabilities": cap_val, "total_assets": asset_val, "period": p},
                        calculated_value=cap_val,
                        reported_value=asset_val,
                        variance=var,
                        status="PASS" if is_ok else "FAIL",
                        notes=f"Capital & Liabilities equals Assets for period {p}." if is_ok else f"Variance {var}",
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name=f"balance_sheet_equation_{p}",
                        formula="total_capital_and_liabilities == total_assets",
                        operands={"period": p},
                        status="NOT_APPLICABLE",
                        notes=f"Missing total_capital_and_liabilities or total_assets for period {p}",
                    )
                )

            # 2.2 Reconcile individual line items to total if line items are categorized
            if line_items:
                cap_lines = [
                    item for item in line_items
                    if item.get("category") in ("capital_and_liabilities", "liabilities", "capital")
                ]
                asset_lines = [
                    item for item in line_items
                    if item.get("category") in ("assets", "asset")
                ]

                if cap_lines and cap_val is not None:
                    calc_cap_sum = sum(
                        parse_financial_number(item.get("values_by_period", {}).get(p, 0)) or 0.0
                        for item in cap_lines
                    )
                    var = calculate_variance(calc_cap_sum, cap_val)
                    is_ok = approx_equal(calc_cap_sum, cap_val, tolerance=self.large_tolerance)
                    checks.append(
                        ValidationCheck(
                            name=f"capital_and_liabilities_breakdown_{p}",
                            formula="sum(capital_and_liability_items) == total_capital_and_liabilities",
                            operands={"sum_items": calc_cap_sum, "period": p},
                            calculated_value=round(calc_cap_sum, 2),
                            reported_value=cap_val,
                            variance=var,
                            status="PASS" if is_ok else "FAIL",
                            notes=f"Reconciles individual capital & liability items for {p}.",
                        )
                    )

                if asset_lines and asset_val is not None:
                    calc_asset_sum = sum(
                        parse_financial_number(item.get("values_by_period", {}).get(p, 0)) or 0.0
                        for item in asset_lines
                    )
                    var = calculate_variance(calc_asset_sum, asset_val)
                    is_ok = approx_equal(calc_asset_sum, asset_val, tolerance=self.large_tolerance)
                    checks.append(
                        ValidationCheck(
                            name=f"assets_breakdown_{p}",
                            formula="sum(asset_items) == total_assets",
                            operands={"sum_items": calc_asset_sum, "period": p},
                            calculated_value=round(calc_asset_sum, 2),
                            reported_value=asset_val,
                            variance=var,
                            status="PASS" if is_ok else "FAIL",
                            notes=f"Reconciles individual asset line items for {p}.",
                        )
                    )

        return checks

    # -------------------------------------------------------------------------
    # 3. Profit & Loss Validations
    # -------------------------------------------------------------------------
    def _validate_profit_and_loss(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        periods = data.get("periods", [])
        if not periods:
            periods = ["default"]

        def get_p_val(key: str, period: str):
            fld = data.get(key, {})
            if isinstance(fld, dict):
                p_obj = fld.get(period)
                if isinstance(p_obj, dict):
                    return parse_financial_number(p_obj.get("value"))
                return parse_financial_number(p_obj)
            return None

        for p in periods:
            # 3.1 Interest Earned + Other Income ≈ Total Income
            int_earned = get_p_val("interest_earned", p)
            other_inc = get_p_val("other_income", p)
            tot_inc = get_p_val("total_income", p)

            if int_earned is not None and other_inc is not None and tot_inc is not None:
                calc_tot_inc = round(int_earned + other_inc, 2)
                var = calculate_variance(calc_tot_inc, tot_inc)
                is_ok = approx_equal(calc_tot_inc, tot_inc, tolerance=self.large_tolerance)
                checks.append(
                    ValidationCheck(
                        name=f"total_income_check_{p}",
                        formula="interest_earned + other_income == total_income",
                        operands={"interest_earned": int_earned, "other_income": other_inc, "period": p},
                        calculated_value=calc_tot_inc,
                        reported_value=tot_inc,
                        variance=var,
                        status="PASS" if is_ok else "FAIL",
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name=f"total_income_check_{p}",
                        formula="interest_earned + other_income == total_income",
                        operands={"period": p},
                        status="NOT_APPLICABLE",
                        notes="Missing income components",
                    )
                )

            # 3.2 Interest Expended + Operating Expenses + Provisions & Contingencies ≈ Total Expenditure
            int_exp = get_p_val("interest_expended", p)
            op_exp = get_p_val("operating_expenses", p)
            prov = get_p_val("provisions_and_contingencies", p)
            tot_exp = get_p_val("total_expenditure", p)

            if int_exp is not None and op_exp is not None and prov is not None and tot_exp is not None:
                calc_tot_exp = round(int_exp + op_exp + prov, 2)
                var = calculate_variance(calc_tot_exp, tot_exp)
                is_ok = approx_equal(calc_tot_exp, tot_exp, tolerance=self.large_tolerance)
                checks.append(
                    ValidationCheck(
                        name=f"total_expenditure_check_{p}",
                        formula="interest_expended + operating_expenses + provisions_and_contingencies == total_expenditure",
                        operands={"interest_expended": int_exp, "operating_expenses": op_exp, "provisions": prov, "period": p},
                        calculated_value=calc_tot_exp,
                        reported_value=tot_exp,
                        variance=var,
                        status="PASS" if is_ok else "FAIL",
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name=f"total_expenditure_check_{p}",
                        formula="interest_expended + operating_expenses + provisions == total_expenditure",
                        operands={"period": p},
                        status="NOT_APPLICABLE",
                        notes="Missing expenditure components",
                    )
                )

            # 3.3 Total Income - Total Expenditure ≈ Net Profit before Minority Interest
            net_profit = get_p_val("net_profit_for_year", p)
            if tot_inc is not None and tot_exp is not None and net_profit is not None:
                calc_net_prof = round(tot_inc - tot_exp, 2)
                var = calculate_variance(calc_net_prof, net_profit)
                is_ok = approx_equal(calc_net_prof, net_profit, tolerance=self.large_tolerance)
                checks.append(
                    ValidationCheck(
                        name=f"net_profit_check_{p}",
                        formula="total_income - total_expenditure == net_profit_for_year",
                        operands={"total_income": tot_inc, "total_expenditure": tot_exp, "period": p},
                        calculated_value=calc_net_prof,
                        reported_value=net_profit,
                        variance=var,
                        status="PASS" if is_ok else "FAIL",
                    )
                )

            # 3.4 Profit before Minority Interest - Minority Interest + Share in Associates ≈ Group Profit
            min_int = get_p_val("minority_interest", p) or 0.0
            assoc_share = get_p_val("share_in_associates", p) or 0.0
            group_prof = get_p_val("consolidated_net_profit_group", p)

            if net_profit is not None and group_prof is not None:
                calc_group_prof = round(net_profit - min_int + assoc_share, 2)
                var = calculate_variance(calc_group_prof, group_prof)
                is_ok = approx_equal(calc_group_prof, group_prof, tolerance=self.large_tolerance)
                checks.append(
                    ValidationCheck(
                        name=f"consolidated_group_profit_check_{p}",
                        formula="net_profit - minority_interest + share_in_associates == group_profit",
                        operands={"net_profit": net_profit, "minority_interest": min_int, "associates_share": assoc_share, "period": p},
                        calculated_value=calc_group_prof,
                        reported_value=group_prof,
                        variance=var,
                        status="PASS" if is_ok else "FAIL",
                    )
                )

            # 3.5 Appropriations check: Group Profit + Amalgamation + Brought Forward ≈ Total Available for Appropriation
            bf_profit = get_p_val("balance_brought_forward", p)
            amal_impact = get_p_val("amalgamation_impact", p) or 0.0
            tot_approp = get_p_val("total_appropriations", p)

            if group_prof is not None and bf_profit is not None and tot_approp is not None:
                calc_approp = round(group_prof + amal_impact + bf_profit, 2)
                var = calculate_variance(calc_approp, tot_approp)
                is_ok = approx_equal(calc_approp, tot_approp, tolerance=self.large_tolerance)
                checks.append(
                    ValidationCheck(
                        name=f"appropriations_available_check_{p}",
                        formula="group_profit + amalgamation_impact + balance_brought_forward == total_appropriations",
                        operands={"group_profit": group_prof, "amalgamation_impact": amal_impact, "balance_brought_forward": bf_profit, "period": p},
                        calculated_value=calc_approp,
                        reported_value=tot_approp,
                        variance=var,
                        status="PASS" if is_ok else "FAIL",
                    )
                )

        return checks

    # -------------------------------------------------------------------------
    # 4. Cash Flow Statement Validations
    # -------------------------------------------------------------------------
    def _validate_cash_flow(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        periods = data.get("periods", [])
        if not periods:
            periods = ["default"]

        def get_cf_val(key: str, period: str):
            fld = data.get(key, {})
            if isinstance(fld, dict):
                p_obj = fld.get(period)
                if isinstance(p_obj, dict):
                    return parse_financial_number(p_obj.get("value"))
                return parse_financial_number(p_obj)
            return None

        for p in periods:
            op_cf = get_cf_val("operating_cash_flow", p)
            inv_cf = get_cf_val("investing_cash_flow", p)
            fin_cf = get_cf_val("financing_cash_flow", p)
            fx_adj = get_cf_val("fx_translation_adjustment", p) or 0.0
            net_increase = get_cf_val("net_increase_in_cash", p)

            # 4.1 Net Cash Flow from Operating + Investing + Financing + FX ≈ Net Increase in Cash & Cash Equivalents
            if op_cf is not None and inv_cf is not None and fin_cf is not None and net_increase is not None:
                calc_net_increase = round(op_cf + inv_cf + fin_cf + fx_adj, 2)
                var = calculate_variance(calc_net_increase, net_increase)
                is_ok = approx_equal(calc_net_increase, net_increase, tolerance=self.large_tolerance)
                checks.append(
                    ValidationCheck(
                        name=f"net_cash_flow_reconciliation_{p}",
                        formula="operating_cf + investing_cf + financing_cf + fx_adjustment == net_increase_in_cash",
                        operands={"operating_cf": op_cf, "investing_cf": inv_cf, "financing_cf": fin_cf, "fx_adj": fx_adj, "period": p},
                        calculated_value=calc_net_increase,
                        reported_value=net_increase,
                        variance=var,
                        status="PASS" if is_ok else "FAIL",
                        notes=f"Reconciled net change in cash for {p}." if is_ok else f"Variance {var}",
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name=f"net_cash_flow_reconciliation_{p}",
                        formula="operating_cf + investing_cf + financing_cf + fx_adj == net_increase_in_cash",
                        operands={"period": p},
                        status="NOT_APPLICABLE",
                        notes="Missing operating, investing, or financing cash flows",
                    )
                )

            # 4.2 Opening Cash + Net Increase + Amalgamation Cash ≈ Closing Cash
            opening_cash = get_cf_val("opening_cash", p)
            amal_cash = get_cf_val("amalgamation_cash", p) or 0.0
            closing_cash = get_cf_val("closing_cash", p)

            if opening_cash is not None and net_increase is not None and closing_cash is not None:
                calc_closing = round(opening_cash + net_increase + amal_cash, 2)
                var = calculate_variance(calc_closing, closing_cash)
                is_ok = approx_equal(calc_closing, closing_cash, tolerance=self.large_tolerance)
                checks.append(
                    ValidationCheck(
                        name=f"closing_cash_reconciliation_{p}",
                        formula="opening_cash + net_increase_in_cash + amalgamation_cash == closing_cash",
                        operands={"opening_cash": opening_cash, "net_increase": net_increase, "amalgamation_cash": amal_cash, "period": p},
                        calculated_value=calc_closing,
                        reported_value=closing_cash,
                        variance=var,
                        status="PASS" if is_ok else "FAIL",
                        notes=f"Closing cash reconciled for period {p}." if is_ok else f"Variance {var}",
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name=f"closing_cash_reconciliation_{p}",
                        formula="opening_cash + net_increase + amalgamation_cash == closing_cash",
                        operands={"period": p},
                        status="NOT_APPLICABLE",
                        notes="Missing opening or closing cash numbers",
                    )
                )

        return checks
