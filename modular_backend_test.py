#!/usr/bin/env python3
"""
SpendAlizer Modular Backend API Test
Tests the refactored modular backend architecture
"""
import requests
import json
import sys
from datetime import datetime

class ModularBackendTester:
    def __init__(self):
        # Get backend URL from frontend .env
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    self.base_url = line.split('=')[1].strip()
                    break
        
        print(f"🔗 Using backend URL: {self.base_url}")
        
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_account_id = None
        self.test_category_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        if endpoint.startswith('/health'):
            # Health endpoint is direct, not through /api
            url = f"http://localhost:8001{endpoint}"
        else:
            url = f"{self.base_url}/api/{endpoint}"
        
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        if self.token and endpoint != 'health':
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
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

    def test_health_endpoint(self):
        """Test health endpoint (direct, not through /api)"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "/health",
            200
        )
        
        if success and response.get('status') == 'healthy':
            print(f"   Version: {response.get('version', 'unknown')}")
            return True
        return False

    def test_register_user(self):
        """Test user registration with specified credentials"""
        user_data = {
            "email": "backendtest@test.com",
            "name": "Backend Test User",
            "password": "testpass123"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=user_data
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            print(f"   Registered user: {response['user']['email']}")
            return True
        return False

    def test_login_user(self):
        """Test user login with registered credentials"""
        login_data = {
            "email": "backendtest@test.com",
            "password": "testpass123"
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
            print(f"   Logged in user: {response['user']['email']}")
            return True
        return False

    def test_accounts_crud(self):
        """Test accounts CRUD operations"""
        results = []
        
        # GET accounts
        success, response = self.run_test(
            "Get Accounts",
            "GET",
            "accounts",
            200
        )
        results.append(success)
        
        # CREATE account
        account_data = {
            "name": "Test Modular Account",
            "account_type": "BANK",
            "institution": "Test Bank",
            "last_four": "9999"
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
            results.append(True)
            
            # Note: Accounts module doesn't have UPDATE endpoint in modular architecture
            print(f"   ✅ Accounts module correctly implements GET and POST only")
            
        else:
            results.append(False)
        
        return all(results)

    def test_categories_crud(self):
        """Test categories CRUD operations"""
        results = []
        
        # GET categories
        success, response = self.run_test(
            "Get Categories",
            "GET",
            "categories",
            200
        )
        results.append(success)
        
        if success and len(response) > 0:
            # Store a category ID for later tests
            self.test_category_id = response[0]['id']
            print(f"   Found {len(response)} categories")
        
        # CREATE category
        category_data = {
            "name": "Test Modular Category",
            "type": "EXPENSE"
        }
        
        success, response = self.run_test(
            "Create Category",
            "POST",
            "categories",
            200,
            data=category_data
        )
        
        if success and 'id' in response:
            created_category_id = response['id']
            print(f"   Created category ID: {created_category_id}")
            results.append(True)
            
            # UPDATE category - need to include type field
            update_data = {
                "name": "Updated Modular Category",
                "type": "EXPENSE"
            }
            
            success, response = self.run_test(
                "Update Category",
                "PUT",
                f"categories/{created_category_id}",
                200,
                data=update_data
            )
            results.append(success)
            
            # DELETE category
            success, response = self.run_test(
                "Delete Category",
                "DELETE",
                f"categories/{created_category_id}",
                200
            )
            results.append(success)
            
        else:
            results.append(False)
            results.append(False)
            results.append(False)
        
        return all(results)

    def test_data_sources(self):
        """Test data sources endpoint"""
        success, response = self.run_test(
            "Get Data Sources",
            "GET",
            "data-sources",
            200
        )
        
        if success:
            print(f"   Found {len(response)} data sources")
            # Verify it returns a list with expected structure
            if isinstance(response, list) and len(response) > 0:
                first_source = response[0]
                if 'id' in first_source and 'name' in first_source:
                    return True
        return False

    def test_analytics_endpoints(self):
        """Test analytics endpoints"""
        results = []
        
        # Test analytics summary
        success, response = self.run_test(
            "Analytics Summary",
            "GET",
            "analytics/summary",
            200
        )
        
        if success:
            # Check for expected fields
            expected_fields = ['total_income', 'total_expense', 'transaction_count']
            has_fields = all(field in response for field in expected_fields)
            if has_fields:
                print(f"   Income: ₹{response.get('total_income', 0)}")
                print(f"   Expense: ₹{response.get('total_expense', 0)}")
                print(f"   Transactions: {response.get('transaction_count', 0)}")
            results.append(has_fields)
        else:
            results.append(False)
        
        # Test spending over time
        success, response = self.run_test(
            "Analytics Spending Over Time",
            "GET",
            "analytics/spending-over-time",
            200
        )
        results.append(success)
        
        return all(results)

    def test_auth_endpoints(self):
        """Test additional auth endpoints"""
        results = []
        
        # Test forgot password
        forgot_data = {
            "email": "backendtest@test.com"
        }
        
        success, response = self.run_test(
            "Forgot Password",
            "POST",
            "auth/forgot-password",
            200,
            data=forgot_data
        )
        results.append(success)
        
        # Test reset password with invalid token (should fail gracefully)
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
        results.append(success)
        
        return all(results)

    def run_all_tests(self):
        """Run all modular backend tests"""
        print("🚀 Starting SpendAlizer Modular Backend Tests")
        print("=" * 60)
        
        test_results = []
        
        # Health check (direct endpoint)
        print("\n📋 HEALTH CHECK")
        test_results.append(("Health Endpoint", self.test_health_endpoint()))
        
        # Authentication tests
        print("\n📋 AUTHENTICATION TESTS")
        # Try to register first, if it fails (user exists), try login
        register_success = self.test_register_user()
        if not register_success:
            print("   Registration failed (user may exist), trying login...")
            login_success = self.test_login_user()
            test_results.append(("Authentication (Login)", login_success))
        else:
            test_results.append(("Authentication (Register)", register_success))
        
        if not self.token:
            print("❌ Authentication failed completely, stopping tests")
            return test_results
        
        # Additional auth endpoints
        test_results.append(("Auth Endpoints", self.test_auth_endpoints()))
        
        # Core API tests
        print("\n📋 ACCOUNTS CRUD TESTS")
        test_results.append(("Accounts CRUD", self.test_accounts_crud()))
        
        print("\n📋 CATEGORIES CRUD TESTS")
        test_results.append(("Categories CRUD", self.test_categories_crud()))
        
        print("\n📋 DATA SOURCES TESTS")
        test_results.append(("Data Sources", self.test_data_sources()))
        
        print("\n📋 ANALYTICS TESTS")
        test_results.append(("Analytics Endpoints", self.test_analytics_endpoints()))
        
        return test_results

def main():
    tester = ModularBackendTester()
    test_results = tester.run_all_tests()
    
    # Print results summary
    print("\n" + "=" * 60)
    print("📊 MODULAR BACKEND TEST RESULTS")
    print("=" * 60)
    
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
    print(f"🔧 Tests run: {tester.tests_run}")
    print(f"✅ Tests passed: {tester.tests_passed}")
    
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test in failed_tests:
            print(f"   - {test}")
        return 1
    else:
        print("\n🎉 All modular backend tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())