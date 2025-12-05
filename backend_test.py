import requests
import sys
import json
from datetime import datetime
import os

class SpendAlizerAPITester:
    def __init__(self, base_url="https://spend-tracker-140.preview.emergentagent.com"):
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
    
    # Delete All Transactions Tests
    print("\n📋 DELETE ALL TRANSACTIONS TESTS")
    test_results.append(("Create Test Transactions", tester.create_test_transactions()))  # Create some test data
    test_results.append(("Verify Test Transactions Created", tester.test_get_transactions()))
    test_results.append(("Delete All - Wrong Confirmation", tester.test_delete_all_transactions_wrong_confirmation()))
    
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