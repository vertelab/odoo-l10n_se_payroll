"""Payroll demo: give the Swedish salary rules accounts and a structure.

Two things are needed before a payslip can be posted, and neither belongs
in the shared payroll modules:

1. **Accounts on the salary rules.** The Swedish rules carry no accounts
   (Tiichri never posted anything), and OCA's payroll_account skips a line
   whose rule has no debit or credit account. The demo maps rule code ->
   account code once, here, instead of editing 93 shared rules.

2. **A structure for the demo company.** The Tiichri structures belong to
   Tiichri's company and the module is course material, so the demo builds
   its own structure from the same rules. The rule list is the Tiichri
   tj_man list, which is the one verified against the external facit.
"""
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Salary rule code -> (debit account code, credit account code) in se_K2.
#   7010  Löner till kollektivanställda
#   7210  Löner till tjänstemän
#   7090  Förändring av semesterlöneskuld
#   7310  Extra kontantersättning
#   7320  Traktamenten vid tjänsteresa
#   7330  Bilersättningar
#   7385  Kostnad för fri bil
#   7390  Övriga ersättningar och förmåner
#   7410  Pensionsförsäkringspremier
#   7510  Arbetsgivaravgifter
#   2710  Personalskatt
#   2731  Avräkning lagstadgade sociala avgifter
#   2890  Övriga kortfristiga skulder (nettolön)
RULE_ACCOUNTS = {
    'gl': ('7210', None),
    'gl_tim': ('7210', None),
    'dl': ('7210', None),
    'enkel_otid': ('7210', None),
    'kval_otid': ('7210', None),
    'bonus': ('7210', None),
    'forman_carbru': ('7385', None),
    'drivmedel_fmn': ('7385', None),
    'ovrig_fmn': ('7390', None),
    'lon_vax': (None, '7090'),
    'sjk_114': (None, '7210'),
    'sjk_15_90_tj': (None, '7210'),
    'sjk_15_90_arb': (None, '7010'),
    'sjk_lon': ('7210', None),
    'sjk_kar': (None, '7210'),
    'vab_avg': (None, '7210'),
    'tjl_tim': (None, '7210'),
    'tjl_kort': (None, '7210'),
    'tjl_lang': (None, '7210'),
    'f_led_tj': (None, '7210'),
    'f_led_arb': (None, '7010'),
    'f_lon_tj': ('7210', None),
    'lunch_kupong': (None, '7390'),
    'trakt_skatt': ('7320', None),
    'mil_skatt': ('7330', None),
    'bensin_mil_skatt': ('7330', None),
    'res_vardag': ('7310', None),
    'res_helg': ('7310', None),
    'skatt_tabell': (None, '2710'),
    'skatt_engang': (None, '2710'),
    'sa': ('7510', '2731'),
    'nl': (None, '2890'),
}

NET_WAGE_ACCOUNT = '2890'
BANK_ACCOUNT = '1930'

# The Tiichri tj_man rule list — the rules verified against the external
# facit. Codes are resolved to rules at install time.
STRUCTURE_RULES = [
    ('l10n_se_hr_payroll', 'hr_salary_rule_sick_deduction_15_90_tj'),
    ('l10n_se_hr_holidays', 'hr_salary_rule_expired_saved_leaves'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_gl'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_dl'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_sick_deduction_1_14'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_wage_exchange'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_attachment_deduction'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_oresavrundning'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_sick_leave'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_qualifying_deduction'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_sick_wage'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_parental_deduction_tj'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_parental_pay_tj'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_parental_leave'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_vab'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_leave_of_absence'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_leave_of_absence_hourly'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_leave_of_absence_less_than_5'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_leave_of_absence_more_than_5'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_kval_otid'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_enkel_otid'),
    ('l10n_se_hr_holidays', 'hr_salary_rule_legal_leave'),
    ('l10n_se_hr_holidays', 'hr_salary_rule_saved_leave'),
    ('l10n_se_hr_holidays', 'hr_salary_rule_legal_leave_deduction_monthly'),
    ('l10n_se_hr_holidays', 'hr_salary_rule_legal_leave_unpaid'),
    ('l10n_se_hr_holidays', 'hr_salary_rule_advance_leave'),
    ('l10n_se_hr_holidays', 'hr_salary_rule_advance_leave_display'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_restid_parent'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_restid_vardag'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_restid_helg'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_mil_parent'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_mil_fri'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_mil_skatt'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_mil_bensin_fri'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_mil_bensin_skatt'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_ovrig_netto_ers'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_ovrig_netto_avd'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_representation_ers'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_bonus'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_brutto'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_summa'),
    ('l10n_se_hr_payroll_benefits', 'hr_benefit_rule_carbru'),
    ('l10n_se_hr_payroll_benefits', 'hr_benefit_rule_home'),
    ('l10n_se_hr_payroll_benefits', 'hr_benefit_rule_home_not_small'),
    ('l10n_se_hr_payroll_benefits', 'hr_benefit_rule_drivmedel'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_parent'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_hel'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_halv'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_natt'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_utland'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_inrikes_skatt'),
    ('l10n_se_hr_payroll_benefits', 'hr_benefit_rule_kost_frukost'),
    ('l10n_se_hr_payroll_benefits', 'hr_benefit_rule_kost_lunch'),
    ('l10n_se_hr_payroll_benefits', 'hr_benefit_rule_kost_fri'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_red_frukost'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_red_lunch'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_red_fri'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_red_utl_frukost'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_red_utl_lunch'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_trakt_red_utl_fri'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_rut_red'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_rut_fmn'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_rut_parent'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_lunch_parent'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_lunch_kupong'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_lunch_kupong_fmn'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_ovrig_fmn_skatt'),
    ('l10n_se_hr_payroll_benefits', 'hr_salary_rule_forman_parent'),
    ('l10n_se_payroll_taxtable', 'hr_salary_rule_prel_tax_table'),
    ('l10n_se_payroll_taxtable', 'hr_salary_rule_one_off_tax'),
    ('l10n_se_payroll_taxtable', 'hr_salary_rule_total_tax_display'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_sa'),
    ('l10n_se_hr_payroll', 'hr_salary_rule_optional_brutil'),
]

STRUCTURE_CONSTANTS = [
    ('MAT', 'Månadsarbetstid i timmar heltid', 175.0),
    ('MAD', 'Månadsarbetstid i dagar heltid', 21.0),
    ('EO', 'Divisor enkel övertid', 94.0),
    ('KO', 'Divisor kvalificerad övertid', 72.0),
    ('PBB', 'Prisbasbelopp', 48300.0),
    ('F_MIL_BENSIN', 'Milersättning (Tjänstebil, bensin)', 0.95),
    ('S_MIL_BENSIN', 'Skattepliktig milersättning (Tjänstebil, bensin)', 0.55),
    ('F_MIL_EGEN', 'Milersättning (Egen bil)', 1.85),
    ('S_MIL_EGEN', 'Skattepliktig milersättning (Egen bil)', 1.15),
    ('RES_VARD', 'Restidsersättning Vardag', 240.0),
    ('RES_HELG', 'Restidsersättning Helg', 190.0),
    ('DRIV_UH', 'Drivmedel Upphöjt värde', 1.2),
    ('TRAKT_HEL', 'Traktamente Heldag', 240.0),
    ('TRAKT_HALV', 'Traktamente Halvdag', 120.0),
    ('TRAKT_NATT', 'Traktamente Natt', 120.0),
    ('KOST_FRUKOST', 'Kostförmån Frukost', 50.0),
    ('KOST_LUNCH', 'Kostförmån Lunch/Middag', 100.0),
    ('KOST_FRI', 'Kostförmån Helt fri', 250.0),
    ('U_RED_FRUKOST', 'Avdrag Frukost (utland)', 0.15),
    ('U_RED_LUNCH', 'Avdrag Lunch/Middag (utland)', 0.35),
    ('U_RED_FRI', 'Avdrag Helt Fri (utland)', 0.85),
    ('RED_FRUKOST', 'Avdrag Frukost', 48.0),
    ('RED_LUNCH', 'Avdrag Lunch/Middag', 84.0),
    ('RED_FRI', 'Avdrag Helt fri', 216.0),
    ('PRIS', 'Lunchkuponger (Pris)', 900.0),
    ('VARDE', 'Lunchkuponger (Förmånsvärde)', 600.0),
    ('AGEU_PCT', 'AG-avgift Ungdom (under 26)', 0.1976),
    ('AGEN_PCT', 'AG-avgift Normal (26-64)', 0.3142),
    ('AGEP_PCT', 'AG-avgift Pensionär (65-76)', 0.1021),
    ('AGEPX_PCT', 'AG-avgift Äldre (77+)', 0.0),
]


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def _payroll_demo_company(self):
        return self.env.ref('l10n_se_demo_company.company')

    @api.model
    def _payroll_demo_account(self, code):
        """Find an account by BAS code for the demo company.

        se_K2 stores the code in code_store under key "3", so the ORM
        `code` field returns nothing. Same lookup as the accounting demo.
        """
        if not code:
            return self.env['account.account']
        company = self._payroll_demo_company()
        self.env.cr.execute("""
            SELECT aa.id
              FROM account_account aa
              JOIN account_account_res_company_rel rel
                ON rel.account_account_id = aa.id
             WHERE rel.res_company_id = %s
               AND EXISTS (
                   SELECT 1 FROM jsonb_each_text(aa.code_store) AS kv(k, v)
                    WHERE kv.v = %s)
             LIMIT 1
        """, (company.id, code))
        row = self.env.cr.fetchone()
        return self.env['account.account'].browse(row[0]) if row else \
            self.env['account.account']

    @api.model
    def _payroll_demo_employee(self, xmlid):
        return self.env.ref(f'l10n_se_demo_company.{xmlid}')

    @api.model
    def _payroll_demo_set_rule_accounts(self):
        """Give the Swedish salary rules the accounts the demo posts to.

        The rules are shared between companies (company_id = False), so the
        accounts are set once, on the rules, not per company.
        """
        Rule = self.env['hr.salary.rule']
        missing = set()
        for code, (debit, credit) in RULE_ACCOUNTS.items():
            rules = Rule.search([('code', '=', code)])
            if not rules:
                continue
            vals = {}
            for field, account_code in (('account_debit', debit),
                                        ('account_credit', credit)):
                if not account_code:
                    continue
                account = self._payroll_demo_account(account_code)
                if account:
                    vals[field] = account.id
                else:
                    missing.add(account_code)
            if vals:
                rules.write(vals)
        if missing:
            _logger.warning('payroll_demo: accounts missing from the chart: %s',
                            sorted(missing))

        # The net wage liability has to allow reconciliation: the payment
        # settles it, and Odoo refuses to reconcile on a non-reconcilable
        # account. se_K2 ships 2890 without the flag.
        liability = self._payroll_demo_account(NET_WAGE_ACCOUNT)
        if liability and not liability.reconcile:
            liability.reconcile = True

    @api.model
    def _payroll_demo_structure(self, code):
        """The demo company's salary structure, created on first use.

        Tiichri's structures belong to Tiichri's company and the module is
        course material, so the demo builds its own from the same rules.
        """
        company = self._payroll_demo_company()
        Structure = self.env['hr.payroll.structure']
        structure = Structure.search([
            ('code', '=', code),
            ('company_id', '=', company.id),
        ], limit=1)
        if structure:
            return structure
        rules = self.env['hr.salary.rule']
        for module, xmlid in STRUCTURE_RULES:
            rule = self.env.ref(f'{module}.{xmlid}', raise_if_not_found=False)
            if rule:
                rules |= rule
        structure = Structure.create({
            'name': f'Demo {code}',
            'code': code,
            'company_id': company.id,
            'rule_ids': [(6, 0, rules.ids)],
            'const_ids': [
                (0, 0, {'code': c, 'name': n, 'constant': v})
                for c, n, v in STRUCTURE_CONSTANTS
            ],
        })
        return structure
