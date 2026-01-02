"""Bank statement parsers for various formats."""
import io
import logging
from typing import List, Dict, Any
import pandas as pd


def parse_hdfc_cc_excel(file_content: bytes) -> List[Dict[str, Any]]:
    """
    Parse HDFC Credit Card Excel/XLS statement.
    
    Format details:
    - Header row is at row 16 (index 16)
    - Column 0: Transaction type (Domestic/International)
    - Column 9: Date & Time (format: DD/MM/YYYY / HH:MM)
    - Column 12: Description
    - Column 18: REWARDS points
    - Column 20: AMT (Amount with comma separators like 3,750.00)
    - Column 23: Debit/Credit indicator (empty for debits, 'Cr' for credits)
    """
    try:
        # Try openpyxl first (handles xlsx and some xls files)
        df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
        logging.info(f"HDFC CC: Parsed with openpyxl, shape: {df.shape}")
    except Exception as e:
        logging.warning(f"openpyxl failed, trying xlrd: {e}")
        try:
            df = pd.read_excel(io.BytesIO(file_content), engine='xlrd')
            logging.info(f"HDFC CC: Parsed with xlrd, shape: {df.shape}")
        except Exception as e2:
            # Try HTML parser (some HDFC files are HTML disguised as XLS)
            try:
                dfs = pd.read_html(io.BytesIO(file_content))
                if dfs:
                    df = dfs[0]
                    logging.info(f"HDFC CC: Parsed as HTML, shape: {df.shape}")
                else:
                    raise ValueError("No tables found in HTML")
            except Exception as e3:
                logging.error(f"All parsers failed: {e3}")
                raise ValueError(f"Could not parse HDFC CC file: {str(e3)}")
    
    transactions = []
    
    # Find the header row by looking for "Date" or "AMT" pattern
    header_row_idx = None
    for idx in range(min(25, len(df))):
        row_values = [str(v).lower() for v in df.iloc[idx].values if pd.notna(v)]
        row_str = ' '.join(row_values)
        if 'date' in row_str and ('amt' in row_str or 'amount' in row_str or 'debit' in row_str):
            header_row_idx = idx
            logging.info(f"HDFC CC: Found header at row {idx}")
            break
    
    if header_row_idx is None:
        # Default to row 16 based on known HDFC CC format
        header_row_idx = 16
        logging.info("HDFC CC: Using default header row 16")
    
    # Process transactions starting after header
    for idx in range(header_row_idx + 1, len(df)):
        try:
            row = df.iloc[idx]
            
            # Extract date from column 9 (Date & Time)
            date_time_val = row.iloc[9] if len(row) > 9 else None
            if pd.isna(date_time_val):
                continue
            
            date_str = str(date_time_val).strip()
            # Parse date in DD/MM/YYYY format (with optional time)
            try:
                if '/' in date_str:
                    date_part = date_str.split('/')[0:3]
                    if len(date_part) >= 3:
                        # Handle "DD/MM/YYYY / HH:MM" format
                        date_part_str = '/'.join(date_part[:3]).split()[0]
                        txn_date = pd.to_datetime(date_part_str, format='%d/%m/%Y', dayfirst=True).strftime("%Y-%m-%d")
                    else:
                        txn_date = pd.to_datetime(date_str, dayfirst=True).strftime("%Y-%m-%d")
                else:
                    txn_date = pd.to_datetime(date_str, dayfirst=True).strftime("%Y-%m-%d")
            except Exception as date_err:
                logging.debug(f"HDFC CC: Skipping row {idx}, date parse error: {date_err}")
                continue
            
            # Extract description from column 12
            desc_val = row.iloc[12] if len(row) > 12 else None
            if pd.isna(desc_val):
                continue
            description = str(desc_val).strip()
            
            # Extract amount from column 20 (AMT)
            amt_val = row.iloc[20] if len(row) > 20 else None
            if pd.isna(amt_val):
                continue
            
            # Parse amount (handles comma-separated values like "3,750.00")
            amt_str = str(amt_val).replace(",", "").replace("INR", "").replace("₹", "").strip()
            try:
                amount = abs(float(amt_str))
            except ValueError:
                continue
            
            if amount <= 0:
                continue
            
            # Extract debit/credit indicator from column 23
            dr_cr_val = row.iloc[23] if len(row) > 23 else None
            dr_cr = str(dr_cr_val).strip().lower() if pd.notna(dr_cr_val) else ""
            
            # For credit cards:
            # - Empty or "Dr" = DEBIT (purchase/expense)
            # - "Cr" = CREDIT (payment/refund received)
            direction = "CREDIT" if dr_cr == "cr" else "DEBIT"
            
            # Build raw metadata
            raw_dict = row.to_dict()
            clean_metadata = {str(k): (v if pd.notna(v) else None) for k, v in raw_dict.items()}
            
            transactions.append({
                "date": txn_date,
                "description": description,
                "amount": amount,
                "direction": direction,
                "raw_metadata": clean_metadata
            })
            
        except Exception as row_err:
            logging.debug(f"HDFC CC: Error parsing row {idx}: {row_err}")
            continue
    
    logging.info(f"HDFC CC: Parsed {len(transactions)} transactions")
    return transactions


def parse_hdfc_bank_excel(file_content: bytes) -> List[Dict[str, Any]]:
    """Parse HDFC Bank Excel file."""
    try:
        df = None
        for skip in [20, 0, 10, 15]:
            try:
                temp_df = pd.read_excel(io.BytesIO(file_content), skiprows=skip)
                if any(col for col in temp_df.columns if 'date' in str(col).lower()):
                    df = temp_df
                    logging.info(f"Found headers at row {skip}, loaded {len(df)} rows")
                    break
            except:
                continue
        
        if df is None:
            df = pd.read_excel(io.BytesIO(file_content))
            logging.info(f"Successfully parsed Excel file with {len(df)} rows")
    except Exception as e:
        logging.error(f"Failed to parse Excel file: {e}")
        raise ValueError(f"Could not parse Excel file: {str(e)}")
    
    transactions = []
    
    for _, row in df.iterrows():
        try:
            raw_dict = row.to_dict()
            clean_metadata = {k: (v if pd.notna(v) else None) for k, v in raw_dict.items()}
            
            date_col = next((col for col in df.columns if 'date' in str(col).lower()), None)
            narration_col = next((col for col in df.columns if any(word in str(col).lower() for word in ['narration', 'description', 'particulars'])), None)
            
            if not date_col or not narration_col:
                continue
            
            date_str = str(row[date_col]).strip()
            try:
                txn_date = pd.to_datetime(date_str, dayfirst=True).strftime("%Y-%m-%d")
            except:
                continue
            
            txn = {
                "date": txn_date,
                "description": str(row[narration_col]).strip(),
                "amount": 0.0,
                "direction": "DEBIT",
                "raw_metadata": clean_metadata
            }
            
            withdrawal_col = next((col for col in df.columns if 'withdrawal' in str(col).lower() or 'debit' in str(col).lower()), None)
            deposit_col = next((col for col in df.columns if 'deposit' in str(col).lower() or 'credit' in str(col).lower()), None)
            
            if withdrawal_col and pd.notna(row.get(withdrawal_col)):
                amount_str = str(row[withdrawal_col]).replace(",", "").replace("INR", "").strip()
                try:
                    txn["amount"] = abs(float(amount_str))
                    txn["direction"] = "DEBIT"
                except ValueError:
                    pass
            
            if deposit_col and pd.notna(row.get(deposit_col)):
                amount_str = str(row[deposit_col]).replace(",", "").replace("INR", "").strip()
                try:
                    txn["amount"] = abs(float(amount_str))
                    txn["direction"] = "CREDIT"
                except ValueError:
                    pass
            
            if txn["amount"] > 0:
                transactions.append(txn)
        except Exception as e:
            logging.error(f"Error parsing Excel row: {e}")
            continue
    
    return transactions


def parse_generic_excel(file_content: bytes, data_source: str) -> List[Dict[str, Any]]:
    """Parse generic Excel file - handles .xlsx, .xls, and HTML-based Excel files."""
    df = None
    
    try:
        file_str = file_content[:1000].decode('utf-8', errors='ignore').lower()
        if '<html' in file_str or '<table' in file_str or '<!doctype' in file_str:
            logging.info("Detected HTML-based Excel file, using HTML parser")
            df = pd.read_html(io.BytesIO(file_content))[0]
        else:
            try:
                df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
            except Exception:
                try:
                    df = pd.read_excel(io.BytesIO(file_content), engine='xlrd')
                except Exception:
                    df = pd.read_html(io.BytesIO(file_content))[0]
    except Exception as e:
        logging.error(f"Failed to parse Excel file: {e}")
        raise ValueError(f"Could not parse Excel file.")
    
    transactions = []
    
    date_col = next((col for col in df.columns if any(word in col.lower() for word in ["date", "txn", "transaction"])), None)
    desc_col = next((col for col in df.columns if any(word in col.lower() for word in ["narration", "description", "particulars", "details"])), None)
    
    if not date_col or not desc_col:
        return transactions
    
    for _, row in df.iterrows():
        try:
            clean_metadata = {k: (v if pd.notna(v) else None) for k, v in row.to_dict().items()}
            
            txn = {
                "date": pd.to_datetime(row[date_col]).strftime("%Y-%m-%d"),
                "description": str(row[desc_col]).strip(),
                "amount": 0.0,
                "direction": "DEBIT",
                "raw_metadata": clean_metadata
            }
            
            for col in df.columns:
                col_lower = col.lower()
                if "withdrawal" in col_lower or "debit" in col_lower:
                    if pd.notna(row[col]):
                        txn["amount"] = abs(float(str(row[col]).replace(",", "").replace("INR", "").strip()))
                        txn["direction"] = "DEBIT"
                elif "deposit" in col_lower or "credit" in col_lower:
                    if pd.notna(row[col]):
                        txn["amount"] = abs(float(str(row[col]).replace(",", "").replace("INR", "").strip()))
                        txn["direction"] = "CREDIT"
            
            if txn["amount"] > 0:
                transactions.append(txn)
        except Exception as e:
            logging.error(f"Error parsing Excel row: {e}")
            continue
    
    return transactions


def parse_hdfc_bank_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """Parse HDFC Bank CSV file."""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
            logging.info(f"Successfully decoded CSV with {encoding} encoding")
            break
        except Exception:
            continue
    
    if df is None:
        raise ValueError("Could not decode file.")
    
    transactions = []
    
    for _, row in df.iterrows():
        try:
            clean_metadata = {k: (v if pd.notna(v) else None) for k, v in row.to_dict().items()}
            
            txn = {
                "date": pd.to_datetime(row["Date"], format="%d/%m/%y").strftime("%Y-%m-%d"),
                "description": str(row["Narration"]).strip(),
                "amount": 0.0,
                "direction": "DEBIT",
                "raw_metadata": clean_metadata
            }
            
            withdrawal_col = next((col for col in df.columns if 'withdrawal' in str(col).lower() or 'debit' in str(col).lower()), None)
            deposit_col = next((col for col in df.columns if 'deposit' in str(col).lower() or 'credit' in str(col).lower()), None)
            
            if withdrawal_col and pd.notna(row.get(withdrawal_col)):
                amount_str = str(row[withdrawal_col]).replace(",", "").replace("INR", "").strip()
                try:
                    txn["amount"] = abs(float(amount_str))
                    txn["direction"] = "DEBIT"
                except ValueError:
                    pass
            
            if deposit_col and pd.notna(row.get(deposit_col)):
                amount_str = str(row[deposit_col]).replace(",", "").replace("INR", "").strip()
                try:
                    txn["amount"] = abs(float(amount_str))
                    txn["direction"] = "CREDIT"
                except ValueError:
                    pass
            
            if txn["amount"] > 0:
                transactions.append(txn)
        except Exception as e:
            logging.error(f"Error parsing row: {e}")
            continue
    
    return transactions


def parse_sbi_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """Parse SBI Bank CSV format with multiple header rows."""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
    
    for encoding in encodings:
        try:
            text_content = file_content.decode(encoding)
            lines = text_content.split('\n')
            
            header_line_idx = None
            for idx, line in enumerate(lines):
                if 'Txn Date' in line or 'txn date' in line.lower():
                    header_line_idx = idx
                    break
            
            if header_line_idx is None:
                continue
            
            csv_content = '\n'.join(lines[header_line_idx:])
            df = pd.read_csv(io.StringIO(csv_content))
            logging.info(f"Successfully parsed SBI CSV with {len(df)} rows")
            
            transactions = []
            
            for _, row in df.iterrows():
                try:
                    if pd.isna(row.get('Txn Date')) or pd.isna(row.get('Description')):
                        continue
                    
                    clean_metadata = {k: (v if pd.notna(v) else None) for k, v in row.to_dict().items()}
                    
                    date_str = str(row['Txn Date']).strip()
                    date_obj = pd.to_datetime(date_str, format='%d-%b-%y')
                    description = str(row['Description']).strip()
                    
                    debit_col = [col for col in df.columns if 'debit' in col.lower()][0]
                    credit_col = [col for col in df.columns if 'credit' in col.lower()][0]
                    
                    amount = 0.0
                    direction = "DEBIT"
                    
                    if pd.notna(row[debit_col]):
                        amount_str = str(row[debit_col]).replace(",", "").replace("INR", "").strip()
                        if amount_str:
                            amount = abs(float(amount_str))
                            direction = "DEBIT"
                    elif pd.notna(row[credit_col]):
                        amount_str = str(row[credit_col]).replace(",", "").replace("INR", "").strip()
                        if amount_str:
                            amount = abs(float(amount_str))
                            direction = "CREDIT"
                    
                    if amount > 0:
                        transactions.append({
                            "date": date_obj.strftime("%Y-%m-%d"),
                            "description": description,
                            "amount": amount,
                            "direction": direction,
                            "raw_metadata": clean_metadata
                        })
                except Exception as e:
                    logging.error(f"Error parsing SBI row: {e}")
                    continue
            
            return transactions
            
        except Exception:
            continue
    
    raise ValueError("Could not parse SBI CSV file.")


def parse_generic_csv(file_content: bytes, data_source: str) -> List[Dict[str, Any]]:
    """Parse generic CSV file."""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
            break
        except Exception:
            continue
    
    if df is None:
        raise ValueError("Could not decode file.")
    
    transactions = []
    
    date_col = next((col for col in df.columns if any(word in col.lower() for word in ["date", "txn", "transaction"])), None)
    desc_col = next((col for col in df.columns if any(word in col.lower() for word in ["narration", "description", "particulars", "details"])), None)
    
    if not date_col or not desc_col:
        return transactions
    
    for _, row in df.iterrows():
        try:
            clean_metadata = {k: (v if pd.notna(v) else None) for k, v in row.to_dict().items()}
            
            txn = {
                "date": pd.to_datetime(row[date_col]).strftime("%Y-%m-%d"),
                "description": str(row[desc_col]).strip(),
                "amount": 0.0,
                "direction": "DEBIT",
                "raw_metadata": clean_metadata
            }
            
            for col in df.columns:
                col_lower = col.lower()
                if "withdrawal" in col_lower or "debit" in col_lower:
                    if pd.notna(row[col]):
                        txn["amount"] = abs(float(str(row[col]).replace(",", "").replace("INR", "").strip()))
                        txn["direction"] = "DEBIT"
                elif "deposit" in col_lower or "credit" in col_lower:
                    if pd.notna(row[col]):
                        txn["amount"] = abs(float(str(row[col]).replace(",", "").replace("INR", "").strip()))
                        txn["direction"] = "CREDIT"
            
            if txn["amount"] > 0:
                transactions.append(txn)
        except Exception as e:
            logging.error(f"Error parsing row: {e}")
            continue
    
    return transactions
