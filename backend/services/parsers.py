"""Bank statement parsers for various formats."""
import io
import logging
from typing import List, Dict, Any
import pandas as pd


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
