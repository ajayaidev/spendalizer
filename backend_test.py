import requests
import sys
import json
from datetime import datetime
import os

class SpendAlizerAPITester:
    def __init__(self, base_url="https://finance-ai-29.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_account_id = None
        self.test_category_id = None
        self.test_rule_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if files:
                # Remove Content-Type for file uploads
                headers.pop('Content-Type', None)
                
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method == 'POST':
                if files:
                    response = requests.post(url, headers=headers, data=data, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_register(self):
        """Test user registration"""
        test_user_data = {
            "email": f"test_user_{datetime.now().strftime('%H%M%S')}@example.com",
            "name": "Test User",
            "password": "TestPass123!"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            print(f"   Registered user: {response['user']['email']}")
            return True
        return False

    def test_login(self):
        """Test user login with existing credentials"""
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST", 
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            return True
        return False

    def test_get_accounts(self):
        """Test getting user accounts"""
        success, response = self.run_test(
            "Get Accounts",
            "GET",
            "accounts",
            200
        )
        return success

    def test_create_account(self):
        """Test creating a new account"""
        account_data = {
            "name": "Test HDFC Account",
            "account_type": "BANK",
            "institution": "HDFC Bank",
            "last_four": "1234"
        }
        
        success, response = self.run_test(
            "Create Account",
            "POST",
            "accounts",
            200,
            data=account_data
        )
        
        if success and 'id' in response:
            self.test_account_id = response['id']
            print(f"   Created account ID: {self.test_account_id}")
            return True
        return False

    def test_get_categories(self):
        """Test getting categories"""
        success, response = self.run_test(
            "Get Categories",
            "GET",
            "categories",
            200
        )
        
        if success and len(response) > 0:
            # Store a category ID for later tests
            self.test_category_id = response[0]['id']
            print(f"   Found {len(response)} categories")
            return True
        return False

    def test_get_data_sources(self):
        """Test getting data sources"""
        success, response = self.run_test(
            "Get Data Sources",
            "GET",
            "data-sources",
            200
        )
        
        if success:
            print(f"   Found {len(response)} data sources")
            return True
        return False

    def test_import_csv(self):
        """Test CSV import functionality"""
        if not self.test_account_id:
            print("❌ Skipping CSV import - no test account available")
            return False
            
        csv_file_path = "/tmp/sample_hdfc_bank.csv"
        if not os.path.exists(csv_file_path):
            print(f"❌ CSV file not found: {csv_file_path}")
            return False
            
        try:
            with open(csv_file_path, 'rb') as f:
                files = {'file': ('sample_hdfc_bank.csv', f, 'text/csv')}
                data = {
                    'account_id': self.test_account_id,
                    'data_source': 'HDFC_BANK'
                }
                
                success, response = self.run_test(
                    "Import CSV File",
                    "POST",
                    "import",
                    200,
                    data=data,
                    files=files
                )
                
                if success:
                    print(f"   Imported {response.get('success_count', 0)} transactions")
                    return True
                return False
        except Exception as e:
            print(f"❌ CSV import error: {e}")
            return False

    def test_get_transactions(self):
        """Test getting transactions"""
        success, response = self.run_test(
            "Get Transactions",
            "GET",
            "transactions",
            200
        )
        
        if success:
            transactions = response.get('transactions', [])
            print(f"   Found {len(transactions)} transactions")
            return True
        return False

    def test_create_rule(self):
        """Test creating a categorization rule"""
        if not self.test_category_id:
            print("❌ Skipping rule creation - no test category available")
            return False
            
        rule_data = {
            "pattern": "ZOMATO",
            "match_type": "CONTAINS",
            "category_id": self.test_category_id,
            "priority": 10
        }
        
        success, response = self.run_test(
            "Create Rule",
            "POST",
            "rules",
            200,
            data=rule_data
        )
        
        if success and 'id' in response:
            self.test_rule_id = response['id']
            print(f"   Created rule ID: {self.test_rule_id}")
            return True
        return False

    def test_get_rules(self):
        """Test getting rules"""
        success, response = self.run_test(
            "Get Rules",
            "GET",
            "rules",
            200
        )
        
        if success:
            print(f"   Found {len(response)} rules")
            return True
        return False

    def test_analytics_summary(self):
        """Test analytics summary"""
        success, response = self.run_test(
            "Analytics Summary",
            "GET",
            "analytics/summary",
            200
        )
        
        if success:
            print(f"   Income: ₹{response.get('total_income', 0)}")
            print(f"   Expense: ₹{response.get('total_expense', 0)}")
            print(f"   Transactions: {response.get('transaction_count', 0)}")
            return True
        return False

    def test_import_history(self):
        """Test getting import history"""
        success, response = self.run_test(
            "Import History",
            "GET",
            "imports",
            200
        )
        
        if success:
            print(f"   Found {len(response)} import batches")
            return True
        return False

    def test_forgot_password_valid_email(self):
        """Test forgot password with valid email"""
        forgot_data = {
            "email": "testuser@example.com"
        }
        
        success, response = self.run_test(
            "Forgot Password - Valid Email",
            "POST",
            "auth/forgot-password",
            200,
            data=forgot_data
        )
        
        if success and "message" in response:
            print(f"   Response: {response['message']}")
            return True
        return False

    def test_forgot_password_nonexistent_email(self):
        """Test forgot password with non-existent email (should still return 200)"""
        forgot_data = {
            "email": "nonexistent@example.com"
        }
        
        success, response = self.run_test(
            "Forgot Password - Non-existent Email",
            "POST",
            "auth/forgot-password",
            200,
            data=forgot_data
        )
        
        if success and "message" in response:
            print(f"   Response: {response['message']}")
            return True
        return False

    def test_reset_password_invalid_token(self):
        """Test reset password with invalid token"""
        reset_data = {
            "token": "invalid_token_12345",
            "new_password": "NewPassword123!"
        }
        
        success, response = self.run_test(
            "Reset Password - Invalid Token",
            "POST",
            "auth/reset-password",
            400,
            data=reset_data
        )
        
        if success:
            print(f"   Correctly rejected invalid token")
            return True
        return False

    def test_password_reset_flow(self):
        """Test complete password reset flow with a real user"""
        # Create a test user first
        test_email = f"reset_test_{datetime.now().strftime('%H%M%S')}@example.com"
        register_data = {
            "email": test_email,
            "name": "Reset Test User",
            "password": "OriginalPass123!"
        }
        
        # Register user
        success, response = self.run_test(
            "Register User for Reset Test",
            "POST",
            "auth/register",
            200,
            data=register_data
        )
        
        if not success:
            return False
        
        # Request password reset
        forgot_data = {"email": test_email}
        success, response = self.run_test(
            "Request Password Reset for Real User",
            "POST",
            "auth/forgot-password",
            200,
            data=forgot_data
        )
        
        if success:
            print(f"   Password reset requested for real user")
            return True
        return False

    def create_test_transactions(self):
        """Create test transactions for delete all test using CSV import"""
        if not self.test_account_id:
            print("❌ Cannot create test transactions - missing account")
            return False
        
        # Create a simple CSV content for testing
        csv_content = """Date,Narration,Withdrawal Amt.,Deposit Amt.
15/01/24,Test Transaction 1 - Coffee Shop,150.00,
16/01/24,Test Transaction 2 - Grocery Store,2500.00,
17/01/24,Test Transaction 3 - Salary Credit,,50000.00"""
        
        # Write CSV to a temporary file
        import tempfile
        import os
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(csv_content)
                temp_csv_path = f.name
            
            # Import the CSV file
            with open(temp_csv_path, 'rb') as f:
                files = {'file': ('test_transactions.csv', f, 'text/csv')}
                data = {
                    'account_id': self.test_account_id,
                    'data_source': 'HDFC_BANK'
                }
                
                success, response = self.run_test(
                    "Create Test Transactions via Import",
                    "POST",
                    "import",
                    200,
                    data=data,
                    files=files
                )
                
                # Clean up temp file
                os.unlink(temp_csv_path)
                
                if success and response.get('success_count', 0) > 0:
                    print(f"   ✅ Created {response['success_count']} test transactions")
                    return True
                else:
                    print(f"   ❌ Failed to create test transactions: {response}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Error creating test transactions: {e}")
            return False

    def test_delete_all_transactions_wrong_confirmation(self):
        """Test delete all transactions with wrong confirmation text"""
        delete_data = {
            "confirmation_text": "delete everything"  # Actually wrong text
        }
        
        success, response = self.run_test(
            "Delete All Transactions - Wrong Confirmation",
            "POST",
            "transactions/delete-all",
            400,
            data=delete_data
        )
        
        if success:
            print(f"   Correctly rejected wrong confirmation text")
            return True
        return False

    def test_delete_all_transactions_case_insensitive(self):
        """Test delete all transactions with case-insensitive confirmation"""
        delete_data = {
            "confirmation_text": "delete all"  # lowercase should work (case-insensitive)
        }
        
        success, response = self.run_test(
            "Delete All Transactions - Case Insensitive",
            "POST",
            "transactions/delete-all",
            200,
            data=delete_data
        )
        
        if success and "deleted_count" in response:
            print(f"   Deleted {response['deleted_count']} transactions")
            return True
        return False

    def test_delete_all_transactions_correct_confirmation(self):
        """Test delete all transactions with correct confirmation text"""
        delete_data = {
            "confirmation_text": "DELETE ALL"
        }
        
        success, response = self.run_test(
            "Delete All Transactions - Correct Confirmation",
            "POST",
            "transactions/delete-all",
            200,
            data=delete_data
        )
        
        if success and "deleted_count" in response:
            print(f"   Deleted {response['deleted_count']} transactions")
            return True
        return False

    def verify_transactions_deleted(self):
        """Verify that all transactions are deleted"""
        success, response = self.run_test(
            "Verify Transactions Deleted",
            "GET",
            "transactions",
            200
        )
        
        if success:
            transactions = response.get('transactions', [])
            if len(transactions) == 0:
                print(f"   ✅ All transactions successfully deleted")
                return True
            else:
                print(f"   ❌ {len(transactions)} transactions still exist")
                return False
        return False

    def verify_categories_preserved(self):
        """Verify that categories are preserved after delete all"""
        success, response = self.run_test(
            "Verify Categories Preserved",
            "GET",
            "categories",
            200
        )
        
        if success and len(response) > 0:
            print(f"   ✅ Categories preserved: {len(response)} categories found")
            return True
        else:
            print(f"   ❌ Categories not preserved")
            return False

    def verify_rules_preserved(self):
        """Verify that rules are preserved after delete all"""
        success, response = self.run_test(
            "Verify Rules Preserved",
            "GET",
            "rules",
            200
        )
        
        if success:
            print(f"   ✅ Rules preserved: {len(response)} rules found")
            return True
        return False

    def test_bulk_categorization_by_rules_debug(self):
        """Debug bulk categorization by rules feature"""
        print("\n🔍 DEBUGGING BULK CATEGORIZATION BY RULES")
        print("=" * 60)
        
        # Step 1: Get all rules
        print("\n1️⃣ Checking existing rules...")
        success, rules_response = self.run_test(
            "Get All Rules",
            "GET",
            "rules",
            200
        )
        
        if not success:
            print("❌ Failed to get rules")
            return False
            
        rules = rules_response
        print(f"   Found {len(rules)} rules:")
        
        dividends_rule = None
        for rule in rules:
            print(f"   - Pattern: '{rule['pattern']}', Type: {rule['match_type']}, Category: {rule['category_id']}")
            if rule['pattern'].upper() == "ACH C-" and rule['match_type'] == "STARTS_WITH":
                dividends_rule = rule
                print(f"     ✅ Found target rule: {rule['id']}")
        
        if not dividends_rule:
            print("❌ Target rule 'ACH C-' with STARTS_WITH not found")
            return False
        
        # Step 2: Get ALL transactions to see what happened
        print("\n2️⃣ Checking ALL transactions...")
        success, txn_response = self.run_test(
            "Get All Transactions",
            "GET",
            "transactions?limit=1000",
            200
        )
        
        if not success:
            print("❌ Failed to get transactions")
            return False
            
        all_transactions = txn_response.get('transactions', [])
        print(f"   Found {len(all_transactions)} total transactions:")
        
        ach_transactions = []
        uncategorized_ach = []
        
        for txn in all_transactions:
            description = txn.get('description', '')
            category_id = txn.get('category_id')
            categorisation_source = txn.get('categorisation_source')
            
            if description.upper().startswith("ACH C-"):
                ach_transactions.append(txn)
                print(f"   - ACH Transaction: '{description}'")
                print(f"     Category: {category_id}, Source: {categorisation_source}")
                
                if not category_id:
                    uncategorized_ach.append(txn)
                    print(f"     ❌ UNCATEGORIZED - should be processed!")
                else:
                    print(f"     ✅ Already categorized during import")
        
        print(f"\n   Summary:")
        print(f"   - Total ACH C- transactions: {len(ach_transactions)}")
        print(f"   - Uncategorized ACH C- transactions: {len(uncategorized_ach)}")
        
        # Now get uncategorized transactions
        print("\n2️⃣b Checking uncategorized transactions...")
        success, txn_response = self.run_test(
            "Get Uncategorized Transactions",
            "GET",
            "transactions?uncategorized=true",
            200
        )
        
        if success:
            uncategorized_transactions = txn_response.get('transactions', [])
            print(f"   Found {len(uncategorized_transactions)} uncategorized transactions:")
            
            for txn in uncategorized_transactions:
                description = txn.get('description', '')
                print(f"   - ID: {txn['id'][:8]}... Description: '{description}'")
        
        # Use uncategorized ACH transactions if any, otherwise use all ACH transactions for testing
        matching_transactions = uncategorized_ach if uncategorized_ach else ach_transactions
        
        if not matching_transactions:
            print("❌ No ACH C- transactions found for testing")
            return False
            
        print(f"   Using {len(matching_transactions)} transactions for bulk categorization test")
        
        # Step 3: Test bulk categorization
        print("\n3️⃣ Testing bulk categorization...")
        transaction_ids = [txn['id'] for txn in matching_transactions]
        
        bulk_data = {
            "transaction_ids": transaction_ids
        }
        
        success, bulk_response = self.run_test(
            "Bulk Categorize by Rules",
            "POST",
            "transactions/bulk-categorize-by-rules",
            200,
            data=bulk_data
        )
        
        if not success:
            print("❌ Bulk categorization failed")
            return False
            
        print(f"   Response: {bulk_response}")
        updated_count = bulk_response.get('updated_count', 0)
        rules_available = bulk_response.get('rules_available', 0)
        
        print(f"   Rules available: {rules_available}")
        print(f"   Transactions updated: {updated_count}")
        
        # Step 4: Verify results
        print("\n4️⃣ Verifying results...")
        for txn_id in transaction_ids:
            success, txn_response = self.run_test(
                f"Get Transaction {txn_id[:8]}",
                "GET",
                f"transactions?limit=1000",
                200
            )
            
            if success:
                transactions = txn_response.get('transactions', [])
                updated_txn = next((t for t in transactions if t['id'] == txn_id), None)
                if updated_txn:
                    category_id = updated_txn.get('category_id')
                    categorisation_source = updated_txn.get('categorisation_source')
                    print(f"   Transaction {txn_id[:8]}: Category={category_id}, Source={categorisation_source}")
                    
                    if category_id == dividends_rule['category_id'] and categorisation_source == "RULE":
                        print(f"     ✅ Correctly categorized!")
                    else:
                        print(f"     ❌ Not categorized correctly")
                else:
                    print(f"   ❌ Transaction {txn_id[:8]} not found")
        
        # Check backend logs for debugging
        print("\n5️⃣ Checking backend logs...")
        try:
            import subprocess
            result = subprocess.run(['tail', '-n', '20', '/var/log/supervisor/backend.err.log'], 
                                  capture_output=True, text=True)
            if result.stdout:
                print("   Recent backend errors:")
                print(result.stdout)
        except:
            print("   Could not read backend logs")
        
        return updated_count > 0

    def create_test_rule_and_transactions(self):
        """Create a test rule and matching transactions for debugging"""
        print("\n🔧 Creating test rule and transactions...")
        
        # Get Dividends category
        success, categories_response = self.run_test(
            "Get Categories for Rule Creation",
            "GET",
            "categories",
            200
        )
        
        if not success:
            return False
            
        categories = categories_response
        dividends_category = None
        for cat in categories:
            if cat['name'].upper() == 'DIVIDENDS':
                dividends_category = cat
                break
        
        if not dividends_category:
            print("❌ Dividends category not found")
            return False
            
        print(f"   Found Dividends category: {dividends_category['id']}")
        
        # Create the rule
        rule_data = {
            "pattern": "ACH C-",
            "match_type": "STARTS_WITH",
            "category_id": dividends_category['id'],
            "priority": 10
        }
        
        success, rule_response = self.run_test(
            "Create ACH C- Rule",
            "POST",
            "rules",
            200,
            data=rule_data
        )
        
        if not success:
            return False
            
        print(f"   Created rule: {rule_response['id']}")
        
        # Create test transactions via CSV import
        if not self.test_account_id:
            print("❌ No test account available")
            return False
            
        csv_content = """Date,Narration,Withdrawal Amt.,Deposit Amt.
15/01/24,ACH C- CAMS 2ND INTDIV25 26-425884,,1500.00
16/01/24,ACH C- MUTUAL FUND DIVIDEND,,2500.00
17/01/24,Regular Transfer,500.00,
18/01/24,ACH C- STOCK DIVIDEND PAYMENT,,750.00"""
        
        import tempfile
        import os
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(csv_content)
                temp_csv_path = f.name
            
            with open(temp_csv_path, 'rb') as f:
                files = {'file': ('test_ach_transactions.csv', f, 'text/csv')}
                data = {
                    'account_id': self.test_account_id,
                    'data_source': 'HDFC_BANK'
                }
                
                success, response = self.run_test(
                    "Import ACH Test Transactions",
                    "POST",
                    "import",
                    200,
                    data=data,
                    files=files
                )
                
                os.unlink(temp_csv_path)
                
                if success and response.get('success_count', 0) > 0:
                    print(f"   ✅ Created {response['success_count']} test transactions")
                    return True
                else:
                    print(f"   ❌ Failed to create test transactions: {response}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Error creating test transactions: {e}")
            return False

    def test_rules_export(self):
        """Test exporting rules"""
        success, response = self.run_test(
            "Export Rules",
            "GET",
            "rules/export",
            200
        )
        
        if success:
            print(f"   Exported {len(response)} rules")
            # Verify each rule has required fields
            for rule in response:
                if 'pattern' not in rule or 'match_type' not in rule or 'category_id' not in rule:
                    print(f"   ❌ Rule missing required fields: {rule}")
                    return False
                if 'category_name' not in rule:
                    print(f"   ❌ Rule missing category_name field: {rule}")
                    return False
            print(f"   ✅ All exported rules have required fields including category_name")
            return True
        return False

    def test_rules_import_valid_data(self):
        """Test importing rules with valid data"""
        # First export existing rules to get valid format
        success, exported_rules = self.run_test(
            "Export Rules for Import Test",
            "GET", 
            "rules/export",
            200
        )
        
        if not success:
            print("   ❌ Could not export rules for import test")
            return False
        
        # Store original count
        original_count = len(exported_rules)
        print(f"   Original rules count: {original_count}")
        
        # Delete all existing rules first
        for rule in exported_rules:
            if 'id' in rule:
                self.run_test(
                    f"Delete Rule {rule['id'][:8]}",
                    "DELETE",
                    f"rules/{rule['id']}",
                    200
                )
        
        # Verify rules are deleted
        success, empty_rules = self.run_test(
            "Verify Rules Deleted",
            "GET",
            "rules",
            200
        )
        
        if success and len(empty_rules) == 0:
            print(f"   ✅ All rules deleted successfully")
        else:
            print(f"   ❌ Rules not deleted properly: {len(empty_rules)} remaining")
            return False
        
        # Import the exported rules back
        import_data = {"rules": exported_rules}
        
        success, response = self.run_test(
            "Import Valid Rules",
            "POST",
            "rules/import",
            200,
            data=import_data
        )
        
        if success:
            imported_count = response.get('imported_count', 0)
            skipped_count = response.get('skipped_count', 0)
            print(f"   Imported: {imported_count}, Skipped: {skipped_count}")
            
            # Verify rules were recreated
            success, new_rules = self.run_test(
                "Verify Rules Imported",
                "GET",
                "rules",
                200
            )
            
            if success and len(new_rules) == imported_count:
                print(f"   ✅ Rules successfully imported and verified")
                return True
            else:
                print(f"   ❌ Rule count mismatch: expected {imported_count}, got {len(new_rules)}")
                return False
        return False

    def test_rules_import_invalid_category(self):
        """Test importing rules with non-existent category_id"""
        invalid_rules = [{
            "pattern": "INVALID_TEST",
            "match_type": "CONTAINS",
            "category_id": "non-existent-category-id-12345",
            "priority": 10
        }]
        
        import_data = {"rules": invalid_rules}
        
        success, response = self.run_test(
            "Import Rules with Invalid Category",
            "POST",
            "rules/import",
            200,
            data=import_data
        )
        
        if success:
            imported_count = response.get('imported_count', 0)
            skipped_count = response.get('skipped_count', 0)
            
            if imported_count == 0 and skipped_count == 1:
                print(f"   ✅ Correctly skipped rule with invalid category")
                return True
            else:
                print(f"   ❌ Expected 0 imported, 1 skipped. Got {imported_count} imported, {skipped_count} skipped")
                return False
        return False

    def test_rules_import_empty_array(self):
        """Test importing empty rules array"""
        import_data = {"rules": []}
        
        success, response = self.run_test(
            "Import Empty Rules Array",
            "POST",
            "rules/import",
            200,
            data=import_data
        )
        
        if success:
            imported_count = response.get('imported_count', 0)
            skipped_count = response.get('skipped_count', 0)
            
            if imported_count == 0 and skipped_count == 0:
                print(f"   ✅ Correctly handled empty rules array")
                return True
            else:
                print(f"   ❌ Expected 0 imported, 0 skipped. Got {imported_count} imported, {skipped_count} skipped")
                return False
        return False

    def create_test_categories_and_rules(self):
        """Create test categories and rules for import/export testing"""
        print("\n🔧 Creating test categories and rules for import/export testing...")
        
        # Get existing categories
        success, categories = self.run_test(
            "Get Categories for Rule Testing",
            "GET",
            "categories",
            200
        )
        
        if not success or len(categories) == 0:
            print("   ❌ No categories available for rule testing")
            return False
        
        # Use first few categories for testing
        test_categories = categories[:3]
        print(f"   Using {len(test_categories)} categories for testing")
        
        # Create test rules
        test_rules_data = [
            {
                "pattern": "ZOMATO",
                "match_type": "CONTAINS",
                "category_id": test_categories[0]['id'],
                "priority": 10
            },
            {
                "pattern": "SWIGGY",
                "match_type": "CONTAINS", 
                "category_id": test_categories[1]['id'],
                "priority": 9
            },
            {
                "pattern": "ACH C-",
                "match_type": "STARTS_WITH",
                "category_id": test_categories[2]['id'] if len(test_categories) > 2 else test_categories[0]['id'],
                "priority": 8
            }
        ]
        
        created_rules = 0
        for rule_data in test_rules_data:
            success, response = self.run_test(
                f"Create Test Rule: {rule_data['pattern']}",
                "POST",
                "rules",
                200,
                data=rule_data
            )
            
            if success:
                created_rules += 1
                print(f"   ✅ Created rule: {rule_data['pattern']}")
            else:
                print(f"   ❌ Failed to create rule: {rule_data['pattern']}")
        
        print(f"   Created {created_rules} test rules")
        return created_rules > 0

    def cleanup_test_data(self):
        """Clean up test data"""
        if self.test_rule_id:
            self.run_test(
                "Delete Test Rule",
                "DELETE",
                f"rules/{self.test_rule_id}",
                200
            )

def main():
    print("🚀 Starting SpendAlizer Backend API Tests")
    print("=" * 50)
    
    tester = SpendAlizerAPITester()
    
    # Test sequence
    test_results = []
    
    # Authentication Tests
    print("\n📋 AUTHENTICATION TESTS")
    test_results.append(("User Registration", tester.test_register()))
    
    if not tester.token:
        print("❌ Registration failed, trying login with default credentials")
        test_results.append(("User Login", tester.test_login()))
    
    if not tester.token:
        print("❌ Authentication failed completely, stopping tests")
        return 1
    
    # Core API Tests
    print("\n📋 CORE API TESTS")
    test_results.append(("Get Accounts", tester.test_get_accounts()))
    test_results.append(("Create Account", tester.test_create_account()))
    test_results.append(("Get Categories", tester.test_get_categories()))
    test_results.append(("Get Data Sources", tester.test_get_data_sources()))
    
    # Import Tests
    print("\n📋 IMPORT TESTS")
    test_results.append(("CSV Import", tester.test_import_csv()))
    test_results.append(("Get Transactions", tester.test_get_transactions()))
    test_results.append(("Import History", tester.test_import_history()))
    
    # Rules Tests
    print("\n📋 RULES TESTS")
    test_results.append(("Create Rule", tester.test_create_rule()))
    test_results.append(("Get Rules", tester.test_get_rules()))
    
    # Analytics Tests
    print("\n📋 ANALYTICS TESTS")
    test_results.append(("Analytics Summary", tester.test_analytics_summary()))
    
    # Forgot Password Tests
    print("\n📋 FORGOT PASSWORD TESTS")
    test_results.append(("Forgot Password - Valid Email", tester.test_forgot_password_valid_email()))
    test_results.append(("Forgot Password - Non-existent Email", tester.test_forgot_password_nonexistent_email()))
    test_results.append(("Reset Password - Invalid Token", tester.test_reset_password_invalid_token()))
    test_results.append(("Password Reset Flow", tester.test_password_reset_flow()))
    
    # Bulk Categorization by Rules Tests
    print("\n📋 BULK CATEGORIZATION BY RULES TESTS")
    test_results.append(("Create Test Rule and Transactions", tester.create_test_rule_and_transactions()))
    test_results.append(("Debug Bulk Categorization by Rules", tester.test_bulk_categorization_by_rules_debug()))
    
    # Delete All Transactions Tests
    print("\n📋 DELETE ALL TRANSACTIONS TESTS")
    test_results.append(("Create Test Transactions", tester.create_test_transactions()))  # Create some test data
    test_results.append(("Verify Test Transactions Created", tester.test_get_transactions()))
    test_results.append(("Delete All - Wrong Confirmation", tester.test_delete_all_transactions_wrong_confirmation()))
    test_results.append(("Delete All - Case Insensitive", tester.test_delete_all_transactions_case_insensitive()))
    
    # Create transactions again for the correct confirmation test
    test_results.append(("Create Test Transactions Again", tester.create_test_transactions()))
    test_results.append(("Delete All - Correct Confirmation", tester.test_delete_all_transactions_correct_confirmation()))
    test_results.append(("Verify Transactions Deleted", tester.verify_transactions_deleted()))
    test_results.append(("Verify Categories Preserved", tester.verify_categories_preserved()))
    test_results.append(("Verify Rules Preserved", tester.verify_rules_preserved()))
    
    # Cleanup
    print("\n📋 CLEANUP")
    tester.cleanup_test_data()
    
    # Print results
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed_tests = []
    failed_tests = []
    
    for test_name, result in test_results:
        if result:
            passed_tests.append(test_name)
            print(f"✅ {test_name}")
        else:
            failed_tests.append(test_name)
            print(f"❌ {test_name}")
    
    print(f"\n📈 Overall: {len(passed_tests)}/{len(test_results)} tests passed")
    
    if failed_tests:
        print(f"\n❌ Failed tests: {', '.join(failed_tests)}")
        return 1
    else:
        print("\n🎉 All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())