import requests
import sys
import json
from datetime import datetime
import os

class SpendAlizerAPITester:
    def __init__(self, base_url="https://budgetpal-270.preview.emergentagent.com"):
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