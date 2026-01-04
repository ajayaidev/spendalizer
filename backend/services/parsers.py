"""Bank statement parsers for various formats."""
import io
import logging
from typing import List, Dict, Any
import pandas as pd


def parse_hdfc_cc_excel(file_content: bytes) -> List[Dict[str, Any]]:
    """
    Parse HDFC Credit Card Excel/XLS statement.
    
    Handles multiple HDFC CC statement formats by dynamically detecting:
    - Header row position
    - Column positions for Date, Description, Amount, Debit/Credit indicator
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
    
    # Find the header row by looking for key column headers
    header_row_idx = None
    date_col = None
    desc_col = None
    amt_col = None
    dr_cr_col = None
    
    for idx in range(min(35, len(df))):
        row = df.iloc[idx]
        row_values = {i: str(v).strip().lower() for i, v in enumerate(row) if pd.notna(v)}
        row_str = ' '.join(row_values.values())
        
        # Look for header row with transaction-related columns
        if ('transaction type' in row_str or 'domestic' in row_str) and ('date' in row_str or 'amt' in row_str):
            header_row_idx = idx
            
            # Map column positions dynamically
            for col_idx, val in row_values.items():
                val_lower = val.lower()
                if 'date' in val_lower and 'time' in val_lower:
                    date_col = col_idx
                elif val_lower == 'date':
                    date_col = col_idx
                elif 'description' in val_lower:
                    desc_col = col_idx
                elif val_lower == 'amt' or val_lower == 'amount':
                    amt_col = col_idx
                elif 'debit' in val_lower and 'credit' in val_lower:
                    dr_cr_col = col_idx
            
            logging.info(f"HDFC CC: Found header at row {idx}, date_col={date_col}, desc_col={desc_col}, amt_col={amt_col}, dr_cr_col={dr_cr_col}")
            break
    
    if header_row_idx is None:
        logging.warning("HDFC CC: Could not find header row, trying fallback detection")
        # Fallback: try to find first row with "Domestic" or "International"
        for idx in range(min(35, len(df))):
            row = df.iloc[idx]
            row_str = ' '.join([str(v).lower() for v in row if pd.notna(v)])
            if 'domestic' in row_str or 'international' in row_str:
                header_row_idx = idx - 1  # Header is one row before data
                break
        
        if header_row_idx is None:
            header_row_idx = 16  # Ultimate fallback
    
    # If columns weren't found, try to detect them from the data
    if date_col is None or desc_col is None or amt_col is None:
        logging.info("HDFC CC: Columns not found in header, detecting from data...")
        first_data_row = df.iloc[header_row_idx + 1] if header_row_idx + 1 < len(df) else None
        
        if first_data_row is not None:
            for col_idx, val in enumerate(first_data_row):
                if pd.notna(val):
                    val_str = str(val).strip()
                    # Detect date column (DD/MM/YYYY pattern)
                    if date_col is None and '/' in val_str and len(val_str) >= 10:
                        parts = val_str.split('/')
                        if len(parts) >= 3 and parts[0].isdigit():
                            date_col = col_idx
                    # Detect description (long text with letters)
                    elif desc_col is None and len(val_str) > 20 and any(c.isalpha() for c in val_str):
                        desc_col = col_idx
                    # Detect amount (numeric with optional comma)
                    elif amt_col is None and val_str.replace(',', '').replace('.', '').isdigit():
                        if float(val_str.replace(',', '')) > 0:
                            amt_col = col_idx
        
        logging.info(f"HDFC CC: Detected columns - date={date_col}, desc={desc_col}, amt={amt_col}")
    
    # Process transactions starting after header
    for idx in range(header_row_idx + 1, len(df)):
        try:
            row = df.iloc[idx]
            
            # Skip empty rows or summary rows
            row_values = [v for v in row if pd.notna(v)]
            if len(row_values) < 3:
                continue
            
            # Extract date
            date_val = row.iloc[date_col] if date_col is not None and date_col < len(row) else None
            if pd.isna(date_val):
                continue
            
            date_str = str(date_val).strip()
            txn_date = None
            txn_time = None
            
            try:
                if '/' in date_str:
                    # Split by space to separate date and time parts
                    parts = date_str.split()
                    date_part_str = parts[0].strip()
                    
                    # Parse date (DD/MM/YYYY)
                    txn_date = pd.to_datetime(date_part_str, format='%d/%m/%Y', dayfirst=True).strftime("%Y-%m-%d")
                    
                    # Extract time if available (format: "/ HH:MM" or just "HH:MM")
                    for part in parts[1:]:
                        if ':' in part and part.replace(':', '').replace('/', '').strip().isdigit():
                            time_part = part.replace('/', '').strip()
                            time_parts = time_part.split(':')
                            if len(time_parts) >= 2:
                                try:
                                    hour = int(time_parts[0])
                                    minute = int(time_parts[1])
                                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                                        txn_time = f"{hour:02d}:{minute:02d}:00"
                                except ValueError:
                                    pass
                else:
                    txn_date = pd.to_datetime(date_str, dayfirst=True).strftime("%Y-%m-%d")
            except Exception as date_err:
                logging.debug(f"HDFC CC: Skipping row {idx}, date parse error: {date_err}")
                continue
            
            if not txn_date:
                continue
            
            # Extract description
            desc_val = row.iloc[desc_col] if desc_col is not None and desc_col < len(row) else None
            if pd.isna(desc_val):
                continue
            description = str(desc_val).strip()
            if len(description) < 3:
                continue
            
            # Extract amount
            amt_val = row.iloc[amt_col] if amt_col is not None and amt_col < len(row) else None
            if pd.isna(amt_val):
                continue
            
            amt_str = str(amt_val).replace(",", "").replace("INR", "").replace("₹", "").strip()
            try:
                amount = abs(float(amt_str))
            except ValueError:
                continue
            
            if amount <= 0:
                continue
            
            # Extract debit/credit indicator
            dr_cr = ""
            if dr_cr_col is not None and dr_cr_col < len(row):
                dr_cr_val = row.iloc[dr_cr_col]
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
                "time": txn_time,
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
    """
    Parse generic CSV file with enhanced amount/direction handling.
    
    Handles multiple formats:
    1. Separate Debit/Credit columns
    2. Single Amount column with sign (positive=debit, negative=credit)
    3. Amount column with Dr/Cr indicator column
    """
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
    
    # Find date column
    date_col = next((col for col in df.columns if any(word in col.lower() for word in ["date", "txn", "transaction"])), None)
    
    # Find description column
    desc_col = next((col for col in df.columns if any(word in col.lower() for word in ["narration", "description", "particulars", "details", "memo"])), None)
    
    if not date_col or not desc_col:
        logging.warning(f"Generic CSV: Missing date ({date_col}) or description ({desc_col}) column")
        return transactions
    
    # Find amount-related columns
    withdrawal_col = next((col for col in df.columns if any(word in col.lower() for word in ["withdrawal", "debit"])), None)
    deposit_col = next((col for col in df.columns if any(word in col.lower() for word in ["deposit", "credit"])), None)
    amount_col = next((col for col in df.columns if any(word in col.lower() for word in ["amount", "amt", "value", "sum"])), None)
    
    # Find Dr/Cr indicator column
    dr_cr_col = next((col for col in df.columns if any(word in col.lower() for word in ["dr/cr", "drcr", "type", "indicator"])), None)
    
    logging.info(f"Generic CSV: date={date_col}, desc={desc_col}, withdrawal={withdrawal_col}, deposit={deposit_col}, amount={amount_col}, dr_cr={dr_cr_col}")
    
    for _, row in df.iterrows():
        try:
            clean_metadata = {k: (v if pd.notna(v) else None) for k, v in row.to_dict().items()}
            
            # Parse date
            try:
                txn_date = pd.to_datetime(row[date_col], dayfirst=True).strftime("%Y-%m-%d")
            except:
                continue
            
            txn = {
                "date": txn_date,
                "description": str(row[desc_col]).strip(),
                "amount": 0.0,
                "direction": "DEBIT",
                "raw_metadata": clean_metadata
            }
            
            # Method 1: Separate Debit/Credit columns
            if withdrawal_col and pd.notna(row.get(withdrawal_col)):
                amt_str = str(row[withdrawal_col]).replace(",", "").replace("INR", "").replace("₹", "").strip()
                try:
                    amt = float(amt_str)
                    if amt != 0:
                        txn["amount"] = abs(amt)
                        txn["direction"] = "DEBIT"
                except ValueError:
                    pass
            
            if deposit_col and pd.notna(row.get(deposit_col)):
                amt_str = str(row[deposit_col]).replace(",", "").replace("INR", "").replace("₹", "").strip()
                try:
                    amt = float(amt_str)
                    if amt != 0:
                        txn["amount"] = abs(amt)
                        txn["direction"] = "CREDIT"
                except ValueError:
                    pass
            
            # Method 2: Single Amount column (use sign or Dr/Cr indicator)
            if txn["amount"] == 0 and amount_col and pd.notna(row.get(amount_col)):
                amt_str = str(row[amount_col]).replace(",", "").replace("INR", "").replace("₹", "").strip()
                try:
                    amt = float(amt_str)
                    txn["amount"] = abs(amt)
                    
                    # Check for Dr/Cr indicator column
                    if dr_cr_col and pd.notna(row.get(dr_cr_col)):
                        indicator = str(row[dr_cr_col]).strip().lower()
                        if indicator in ["cr", "credit", "c", "+"]:
                            txn["direction"] = "CREDIT"
                        else:
                            txn["direction"] = "DEBIT"
                    else:
                        # Use sign: positive = debit (expense), negative = credit (income/refund)
                        txn["direction"] = "CREDIT" if amt < 0 else "DEBIT"
                        
                except ValueError:
                    pass
            
            if txn["amount"] > 0:
                transactions.append(txn)
        except Exception as e:
            logging.error(f"Error parsing row: {e}")
            continue
    
    logging.info(f"Generic CSV: Parsed {len(transactions)} transactions")
    return transactions

