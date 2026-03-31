import os
import shutil
import logging
import argparse

from src.models import Record
from src.config import settings
from src.utils import setup_logger
from src.file_handler import FileHandler
from src.data_extractor import DataExtractor
from src.ticker_mapper import get_or_fetch_ticker
from src.name_cleaner import get_or_fetch_clean_name
from src.position_manager import PositionManager
from src.storage import save_portfolio_data, PortfolioStorage
  

def main():
    '''Main function to run the file processing pipeline. 
    Orchestrates single steps.'''
    
    ## Setup Logger ##
    log = setup_logger()
    log.info("Logger initialized.")
  
    ## Check for new Files, Rename and Move ##
    handler = FileHandler(log)
    extractor = DataExtractor(log)
    portfolio_storage = PortfolioStorage(db_path=str(settings.db_path))
    
    ## Set the working directory for the code and file list to be processed ##
    if settings.enable_initialization_portfolio:
        log.info("Initializing portfolio data storage...")
        work_dir = handler.get_destination_directory()
        file_list = handler.get_file_list(work_dir)
        
    else:
        log.info("Using existing portfolio to be extended.")
        log.info("The already initialized portfolio is here:"\
                f"{settings.data_dir}")
        work_dir = handler.get_input_directory()
        file_list = handler.get_file_list(work_dir)

    ## Start processing files using the file list selected above ##
    log.info(f"Processing files in working directory: {work_dir}")
    data = []
    for file in file_list:
        file_path = os.path.join(work_dir, file)
        try:
            ##Extract base text containing all information from PDF
            pdf_text = extractor.read_pdf(file_path)
            
            ##Extract base information needed for further processing and name
            is_crypto = extractor.check_crypto(pdf_text, settings.crypto_tokens)
            event_type = extractor.extract_option(pdf_text, file)
            name = extractor.extract_name(pdf_text, file, is_crypto, event_type)
            date = extractor.extract_date(pdf_text, file)
            isin = extractor.extract_isin(pdf_text, file, is_crypto)

            # 1. Resolve ticker
            ticker = None
            if isin:
                ticker = get_or_fetch_ticker(
                    isin=isin,
                    config=settings,
                    db_connection=portfolio_storage.con,
                    rate_limit_delay=0.5,
                )
            if ticker:
                log.info(f"Resolved ticker for ISIN {isin}: {ticker}")
            else:
                log.warning(f"Could not resolve ticker for ISIN {isin}")

            # 2. Resolve clean name
            clean_name = None
            if ticker:
                clean_name = get_or_fetch_clean_name(
                    isin=isin,
                    ticker=ticker,
                    db_connection=portfolio_storage.con,
                    rate_limit_delay=0.5
                )
                if clean_name:
                    log.info(f"Resolved name for {ticker}: {clean_name}")

            ## Optimize base infos used also for file naming at the end
            name_processed = extractor.optimize_name(name, file)
            date_processed = extractor.optimize_date(date, file)

            #Exchange Rate especially for dividends relative 
            exchange_rate = extractor.extract_exchange_rate(pdf_text, file)
            
            ## The main invoice table contains key information about the
            ## transactions 
            if event_type == 'dividend':
                unit_amount, unit_price, dividend_per_share, gross_amount,\
                currency = extractor.extract_main_invoice_details_dividends(\
                    pdf_text, file, exchange_rate)
            
            elif event_type == 'etf_saving_plan':
                unit_amount, unit_price, dividend_per_share, gross_amount,\
                currency = extractor.extract_main_invoice_details_etf_saving_plan(\
                    pdf_text, file, exchange_rate)
            elif event_type == 'interest':
                gross_amount, currency = extractor.extract_main_invoice_details_interest(\
                    pdf_text, file)
                unit_amount = unit_price = dividend_per_share\
                    = name_processed = exchange_rate = isin = None
            else:
                unit_amount, unit_price, dividend_per_share, gross_amount, currency = \
                extractor.extract_main_invoice_details(\
                    pdf_text, file, is_crypto, exchange_rate)
                        
            ## Extract fees and tax information ##
            external_fee, financial_transaction_tax, foreign_tax, capital_tax, church_tax, soli_tax =\
                extractor.extract_fees_and_tax(pdf_text, file, event_type,\
                                               currency, exchange_rate)
            
            net_cashflow = extractor.extract_net_cashflow(pdf_text, file,\
                                                          event_type, is_crypto)
            record = Record(
                name=name_processed,
                clean_name=clean_name,
                date=date_processed,
                event_type=event_type,
                isin=isin,
                ticker=ticker,
                unit_price=unit_price,
                unit_amount=unit_amount,
                dividend_per_share=dividend_per_share,
                currency=currency,
                exchange_rate=exchange_rate,
                gross_amount=gross_amount,
                net_cashflow=net_cashflow,
                external_fee=external_fee,
                financial_transaction_tax=financial_transaction_tax,
                foreign_tax=foreign_tax,
                capital_tax=capital_tax,
                church_tax=church_tax,
                soli_tax=soli_tax,
                is_crypto=is_crypto,
            )
            log.info(f"Record created for file {file}")
        except Exception as e:
            log.error(f"Error accessing file {file}: {e}")
            continue

        data.append(record)

        filename = handler.get_new_file_name(event_type, date_processed,\
                                             name_processed)
        destination_path = handler.get_destination_directory()

        old_file_path = handler.build_path(work_dir, file)
        new_file_path = handler.build_path(destination_path, filename)

        shutil.move(old_file_path, new_file_path)

    log.info("finished processing all files in the directory.")
    log.info(f"Total Files processed: {len(data)}")
    
    if settings.enable_initialization_portfolio:
        log.info("Initializing a Portfolio Storage Database..")
    else:
        log.info("Portfolio Storage Database will be extended..")

    if data:
        result = save_portfolio_data(data)

    # ========================================================================
    # STEP 2: Backfill missing tickers from database
    # ========================================================================
    log.info("\n" + "="*60)
    log.info("STEP 2: Backfilling missing tickers from database")
    log.info("="*60)
    
    backfilled_tickers = portfolio_storage.backfill_missing_tickers(
        get_ticker_func=get_or_fetch_ticker,
        config=settings,
        rate_limit_delay=0.5
    )
    
    # ========================================================================
    # STEP 2.5: Backfill missing clean names
    # ========================================================================
    log.info("\n" + "="*60)
    log.info("STEP 2.5: Backfilling missing clean names from database")
    log.info("="*60)
    
    backfilled_names = portfolio_storage.backfill_missing_names(
        get_name_func=get_or_fetch_clean_name,
        rate_limit_delay=0.5
    )

    # ========================================================================
    # STEP 3: Recalculate FIFO Positions & History
    # ========================================================================
    log.info("\n" + "="*60)
    log.info("STEP 3: Recalculating FIFO Positions & History")
    log.info("="*60)

    try:
        positions_manager = PositionManager(portfolio_storage.con)
        positions_manager.calculate_fifo()
        log.info("FIFO recalculation complete (positions & trades updated).")
    except Exception as e:
        log.error(f"Error during FIFO recalculation: {e}")
    
    result_csv = portfolio_storage.export_to_csv(settings.csv_path)

    portfolio_storage.close()

    log.info("Finished Data Storage File.")
    log.info("Getting Database Summary.")
    log.info(f"\n{'='*50}")
    if data:
        log.info(f"✓ Added {result['rows_inserted']} transactions to database")
    log.info(f"✓ Backfilled {backfilled_tickers} tickers")
    log.info(f"✓ Backfilled {backfilled_names} names")
    log.info(f"✓ Exported to {result_csv}")
    log.info(f"{'='*50}")
    log.info("Trfolio run completed successfully.")
    log.info(f"{'='*50}")


if __name__ == "__main__":
    main()
