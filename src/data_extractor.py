import re
import logging

from pypdf import PdfReader
from src.utils import parse_money

'''
The DataExtractor module is responsible for extracting the necessary data
from all PDF files at destination path and the write the data to a CSV file.

After initialization the Extractor is used to check for new PDF files to add
to the data storage.
'''
class DataExtractor:
    def __init__(self, log: logging.Logger):
        self.log = log

    def check_crypto(self, text: str, crypto_token: str) -> bool:
        try:
            is_crypto = any(t in text.lower() for t in crypto_token.keys())
        except Exception as e:
            self.log.error(f"Error checking for crypto tokens: {e}")
        return is_crypto

    def read_pdf(self, file_path: str) -> str:
        '''
        The essential information for further processing and extracting data
        from the pdf files is to read the the text content of the pdf, which
        is done in this function.
        Returns the text content of the pdf file.
        '''
        reader = PdfReader(file_path)
        first_page = reader.pages[0]
        text = first_page.extract_text()
        return text

    def optimize_name(self, name: str, file: str) -> str:
        """Optimize the name by removing special characters and spaces."""
        if not name:
            self.log.warning("Name extraction failed for file {file}." \
            " Using 'unknown' as placeholder.")
            return "unknown"
        optimized = re.sub(r'\s*\(.*?\)\s*', '', name)
        optimized = re.sub(r'[^\w\s]', '', name)
        optimized = re.sub(r'\s+', '_', optimized)
        return optimized.lower()

    def optimize_date(self, date: str, file: str) -> str:
        """Optimize the date from DD.MM.YYYY to YYYYMMDD format."""
        if not date:
            return "unknown_date"
        parts = date.split('.')
        if len(parts) == 3:
            return f"{parts[2]}{parts[1].zfill(2)}{parts[0].zfill(2)}"
        else:
            self.log.warning("Date extraction failed for file {file}." \
            " Using 'invalid_date' as placeholder.")
            return "invalid_date"

    def extract_isin(self, text: str, file: str, is_crypto: bool) -> str:
        isin_match = re.search(r'ISIN:\s*([A-Z0-9]+)', text)
        isin = isin_match.group(1) if isin_match else None
        if is_crypto:
            header_match = re.search(r'POSITION ANZAHL PREIS BETRAG\n(.*?)\n',\
                                    text, re.DOTALL)
            isin = header_match.group(1).split()[1].replace('(', '').replace(')', '')
        elif not isin and not is_crypto:
            isin_match = re.search(r'(?m)^POSITION[^\n]*\n([^\n]+)\n([^\n]+)', text)
            if isin_match:
                isin = isin_match.group(2).split()[0]
        if not isin:
            self.log.warning(f"Could not extract ISIN from PDF file {file}.")
        return isin

    def extract_exchange_rate(self, text: str, file: str) -> float:
        exchange_match = re.findall(r'Zwischensumme\s*([0-9.,]+)', text)
        if exchange_match:
            correct_match = exchange_match[1] if len(exchange_match) > 1 else 1
            exchange_rate = parse_money(correct_match) if type(correct_match) == str else float(correct_match)
        else:
            exchange_rate = 1
        return exchange_rate

    def extract_fees_and_tax(self, text: str, file: str,\
                            event: str, currency: str, exchange_rate: float) -> tuple:
        """Extract all fees and taxes from the PDF text.

        Returns a 6-tuple matching the unpacking in main.py:
            external_fee, financial_transaction_tax, foreign_tax,
            capital_tax, church_tax, soli_tax

        Trade Republic does not charge a financial transaction tax,
        so that value is always 0.
        """
        external_fee = 1 if event == 'buy' or event == 'sell' else 0
        # TR does not levy a financial transaction tax — kept as 0 for
        # forward-compatibility with the Record model.
        financial_transaction_tax = 0

        if event == 'sell' or event == 'dividend':
            foreign_tax_match = re.search(r'Quellensteuer.*?([0-9.,]+)(?:\s*[A-Z]{3})?', text)
            foreign_tax = (parse_money(foreign_tax_match.group(1)) /\
                        exchange_rate) if foreign_tax_match else 0

            capital_tax_match = re.search(r'Kapitalertrag(?:s?)?steuer\b(?:.*?\b)?(?:[0-9]+(?:[.,][0-9]+)?\s+)?([0-9]+(?:[.,][0-9]+)?)\s+EUR', text)
            capital_tax = parse_money(capital_tax_match.group(1)) if capital_tax_match else 0

            church_tax_match = re.search(r'Kirchensteuer\b(?:.*?\b)?(?:[0-9]+(?:[.,][0-9]+)?\s+)?([0-9]+(?:[.,][0-9]+)?)\s+EUR', text)
            church_tax = parse_money(church_tax_match.group(1)) if church_tax_match else 0

            soli_tax_match = re.search(r'Solidarit\u00e4tszuschlag\b(?:.*?\b)?(?:[0-9]+(?:[.,][0-9]+)?\s+)?([0-9]+(?:[.,][0-9]+)?)\s+EUR', text)
            soli_tax = parse_money(soli_tax_match.group(1)) if soli_tax_match else 0

        else:
            foreign_tax = 0
            capital_tax = 0
            church_tax = 0
            soli_tax = 0

        return external_fee, financial_transaction_tax, foreign_tax,\
            capital_tax, church_tax, soli_tax

    def extract_net_cashflow(self, text: str, file: str, event_type: str,\
                             is_crypto: bool) -> float:
        if event_type == 'interest':
            cashflow_match = re.search(
                r'GUTSCHRIFT NACH STEUERN.*?([0-9.,]+)\s*EUR', text, re.DOTALL
                )
            cashflow = parse_money(cashflow_match[0].split()[-2]) if cashflow_match else None
        else:
            cashflow_match = re.findall(r'(?m)^\s*GESAMT\b.*?([0-9.,]+)\s*EUR\b', text)

            if len(cashflow_match) > 1:
                cashflow_match_one = parse_money(cashflow_match[0])
                cashflow_match_two = parse_money(cashflow_match[1])
                if event_type == 'buy':
                    cashflow = max(cashflow_match_one, cashflow_match_two)
                elif event_type == 'sell' or event_type == 'dividend':
                    cashflow = min(cashflow_match_one, cashflow_match_two)
            else:
                cashflow = parse_money(cashflow_match[0])
            if not cashflow:
                cashflow = None
        net_cashflow = cashflow
        return net_cashflow

    def extract_main_invoice_details_etf_saving_plan(self, text: str, file: str,\
                                                    exchange_rate: float) -> tuple:
        event_details = re.search\
            (r'POSITION ANZAHL DURCHSCHNITTSKURS BETRAG\n(.*?)\nISIN:[^\n]+\n([^\n]+)',\
            text, re.DOTALL)

        details = None
        details = event_details.group(2).strip()

        unit_amount = unit_price = currency = gross_amount =\
            dividend_per_share = None
        if details:
            details_parts = re.split(r'\s+', details)
            try:
                unit_amount = parse_money(details_parts[0])
            except Exception:
                unit_amount = None
            try:
                unit_price = parse_money(details_parts[2])
            except Exception:
                unit_price = None
            try:
                currency = details_parts[3]
            except Exception:
                currency = None
            try:
                gross_amount = parse_money(details_parts[4]) if currency == 'EUR'\
                    else parse_money(details_parts[4]) / exchange_rate
            except Exception:
                gross_amount = None
        else:
            self.log.warning(f"No details line found in file {file}")

        return unit_amount, unit_price, dividend_per_share,\
                gross_amount, currency

    def extract_main_invoice_details_dividends(self, text: str, file: str,\
                                                exchange_rate: float) -> tuple:
        unit_amount = unit_price = currency = gross_amount =\
            dividend_per_share = None
        details_match = re.search(r'POSITION ANZAHL ERTRAG BETRAG\n(.*?)\n[^\n]+\n([^\n]+)', text, re.DOTALL)
        if len(details_match.group(0).split('\n')[2].split()[1:]) > 1:
            details = details_match.group(0).split('\n')[2].split()[1:]
        else:
            details_match = re.search(r'POSITION ANZAHL ERTRAG BETRAG\n(.*?)\nISIN:[^\n]+\n([^\n]+)', text, re.DOTALL)
            details = details_match.group(2).split()

        if details:
            unit_amount = parse_money(details[0])
            dividend_per_share = parse_money(details[2])
            currency = details[3]
            gross_amount = parse_money(details[4]) if currency == 'EUR'\
                else parse_money(details[4]) / exchange_rate
        else:
            unit_amount = dividend_per_share = gross_amount = currency = None
        return unit_amount, unit_price, dividend_per_share, gross_amount, currency

    def extract_main_invoice_details(self, text: str, file: str,\
                                    is_crypto: bool, exchange_rate: float) -> tuple:
        event_details = re.search\
            (r'POSITION ANZAHL PREIS BETRAG\n(.*?)\nISIN:[^\n]+\n([^\n]+)',\
            text, re.DOTALL)

        crypto_details = re.search(r'POSITION ANZAHL PREIS BETRAG\n(.*?)\n',\
                                   text, re.DOTALL)
        details = None
        if event_details:
            details = event_details.group(2).strip()
        elif crypto_details:
            details = crypto_details.group(1).strip()

        unit_amount = unit_price = currency = gross_amount =\
            dividend_per_share = None
        if details:
            if is_crypto:
                details_parts = re.split(r'\s+', details)[2:]
            else:
                details_parts = re.split(r'\s+', details)

            try:
                unit_amount = parse_money(details_parts[0])
            except Exception:
                unit_amount = None
            try:
                unit_price = parse_money(details_parts[2])
            except Exception:
                unit_price = None
            try:
                currency = details_parts[3]
            except Exception:
                currency = None
            try:
                gross_amount = parse_money(details_parts[4]) if currency == 'EUR'\
                    else parse_money(details_parts[4]) / exchange_rate
            except Exception:
                gross_amount = None
        else:
            self.log.warning(f"No details line found in file {file}")
        return unit_amount, unit_price, dividend_per_share,\
                gross_amount, currency

    def extract_main_invoice_details_interest(self, text: str, file: str) -> float:
        gross_amount_match = re.search(r'Gesamt\s+.*?\n(.*?)\n', text, re.DOTALL)
        if gross_amount_match:
            gross_amount = gross_amount_match.group(0).strip().split()[1]
            gross_amount = parse_money(gross_amount)
            currency = 'EUR'
        else:
            gross_amount = None
            currency = None
        return gross_amount, currency

    def extract_name(self, text: str, file: str, is_crypto: bool,\
                    event_type: str) -> str:

        if event_type == 'dividend':
            name_match = re.findall(r'POSITION ANZAHL ERTRAG BETRAG\n(.*?)\n[^\n]+\n([^\n]+)', text, re.DOTALL)
        elif event_type == 'buy' or event_type == 'sell':
            name_match = re.findall(r'POSITION ANZAHL PREIS BETRAG\n(.*?)\n', text, re.DOTALL)
        else:
            name_match = re.findall(r'POSITION\s+.*?\n(.*?)\n', text, flags=re.DOTALL)

        if not is_crypto:
            name = name_match[0] if name_match else None
            if type(name) is tuple:
                name = name[0]
        else:
            name = name_match[0].split()[0] if name_match else None
        if not name:
            self.log.warning("Could not extract name from PDF file {file}.")

        return name

    def extract_date(self, text: str, file: str) -> str:
        date_match = re.search(r'\u00dcBERSICHT\s*.*?\n.*?(\d{2}\.\d{2}\.\d{4})',\
                               text, flags=re.DOTALL)
        date = date_match.group(1) if date_match else None
        if not date:
            self.log.warning("Could not extract date from PDF file {file}.")
        return date

    def extract_option(self, text: str, file: str) -> str:
        '''
        Function used to extract the option (buy, sell, div) from the text
        of the pdf file.
        '''
        if re.search(r'(?<!ver)kauf\b', text, re.IGNORECASE):
            option = 'buy'
        elif ('verkauf' in text.lower()):
            option = 'sell'
        elif re.search(r'dividende?\s+(?:mit\s+(?:dem\s+)?ex(?:-datum?)?|ex(?:-datum?)?)',\
                text.lower()):
            option = 'dividend'
        elif ('sparplanausf\u00fchrung' in text.lower()):
            option = 'etf_saving_plan'
        elif ('zinsen' in text.lower()):
            option = 'interest'
        else:
            option = 'unknown'
            self.log.warning("Could not extract option from PDF file {file}.\
                            Using 'unknown' as placeholder.")

        return option
