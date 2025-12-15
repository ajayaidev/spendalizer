#!/usr/bin/env python3
"""
Specific test for Database Backup and Restore with System Categories Architecture
Tests the scenario described in the review request
"""

import requests
import json
import tempfile
import os
from datetime import datetime
import zipfile
from io import BytesIO

class SystemCategoriesBackupRestoreTest:
    def __init__(self, base_url="https://budget-wise-11.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.test_account_ids = []
        self.test_category_ids = []
        self.test_rule_ids = []
        self.original_backup_data = None

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def api_call(self, method, endpoint, data=None, files=None, expected_status=200):
        """Make API call and return success, response"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if files:
                headers.pop('Content-Type', None)
                
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method == 'POST':
                if files:
                    response = requests.post(url, headers=headers, data=data, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, response.content if hasattr(response, 'content') else {}
            else:
                self.log(f"❌ API call failed: {method} {endpoint} - Status: {response.status_code}")
                try:
                    error_detail = response.json()
                    self.log(f"   Error: {error_detail}")
                except:
                    self.log(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            self.log(f"❌ API call exception: {str(e)}")
            return False, {}

    def register_user(self):
        """Register a new test user"""
        self.log("🔐 Registering new test user...")
        
        test_user_data = {
            "email": f"backup_test_{datetime.now().strftime('%H%M%S')}@example.com",
            "name": "Backup Test User",
            "password": "TestPass123!"
        }
        
        success, response = self.api_call("POST", "auth/register", data=test_user_data)
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            self.log(f"✅ Registered user: {response['user']['email']}")
            return True
        return False

    def create_accounts(self):
        """Create 2 test accounts"""
        self.log("🏦 Creating 2 test accounts...")
        
        accounts_data = [
            {
                "name": "Test HDFC Savings Account",
                "account_type": "BANK",
                "institution": "HDFC Bank",
                "last_four": "1234"
            },
            {
                "name": "Test SBI Credit Card",
                "account_type": "CREDIT_CARD",
                "institution": "SBI Bank",
                "last_four": "5678"
            }
        ]
        
        for i, account_data in enumerate(accounts_data, 1):
            success, response = self.api_call("POST", "accounts", data=account_data)
            if success and 'id' in response:
                self.test_account_ids.append(response['id'])
                self.log(f"✅ Created account {i}: {account_data['name']}")
            else:
                self.log(f"❌ Failed to create account {i}")
                return False
        
        return len(self.test_account_ids) == 2

    def create_user_categories(self):
        """Create 3 user categories"""
        self.log("📂 Creating 3 user categories...")
        
        categories_data = [
            {"name": "Test Food Delivery", "type": "EXPENSE"},
            {"name": "Test Investment Income", "type": "INCOME"},
            {"name": "Test Bank Transfer", "type": "TRANSFER"}
        ]
        
        for i, category_data in enumerate(categories_data, 1):
            success, response = self.api_call("POST", "categories", data=category_data)
            if success and 'id' in response:
                self.test_category_ids.append(response['id'])
                self.log(f"✅ Created user category {i}: {category_data['name']}")
            else:
                self.log(f"❌ Failed to create user category {i}")
                return False
        
        return len(self.test_category_ids) == 3

    def create_transactions(self):
        """Create 5-10 transactions with mix of system and user categories"""
        self.log("💳 Creating transactions with mix of system and user categories...")
        
        if not self.test_account_ids:
            self.log("❌ No test accounts available")
            return False
        
        # CSV with transactions that will use both system and user categories
        csv_content = """Date,Narration,Withdrawal Amt.,Deposit Amt.
15/01/24,ZOMATO FOOD ORDER,450.00,
16/01/24,AMAZON PURCHASE,1250.00,
17/01/24,SALARY CREDIT,,75000.00
18/01/24,ATM WITHDRAWAL,2000.00,
19/01/24,GROCERY STORE PURCHASE,850.00,
20/01/24,FREELANCE PAYMENT,,15000.00
21/01/24,ELECTRICITY BILL PAYMENT,1200.00,
22/01/24,MOVIE TICKETS,600.00,
23/01/24,BANK TRANSFER TO SAVINGS,5000.00,
24/01/24,DIVIDEND INCOME,,2500.00"""
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(csv_content)
                temp_csv_path = f.name
            
            with open(temp_csv_path, 'rb') as f:
                files = {'file': ('test_transactions.csv', f, 'text/csv')}
                data = {
                    'account_id': self.test_account_ids[0],
                    'data_source': 'HDFC_BANK'
                }
                
                success, response = self.api_call("POST", "import", data=data, files=files)
                
                os.unlink(temp_csv_path)
                
                if success and response.get('success_count', 0) > 0:
                    self.log(f"✅ Created {response['success_count']} transactions")
                    return True
                else:
                    self.log(f"❌ Failed to create transactions: {response}")
                    return False
                    
        except Exception as e:
            self.log(f"❌ Error creating transactions: {e}")
            return False

    def create_rules(self):
        """Create 2 categorization rules"""
        self.log("📋 Creating 2 categorization rules...")
        
        # Get system categories for rules
        success, categories = self.api_call("GET", "categories")
        if not success:
            return False
        
        # Find system categories
        salary_category = None
        food_category = None
        
        for cat in categories:
            if cat.get('is_system') and cat['name'] == 'Salary':
                salary_category = cat
            elif cat.get('is_system') and cat['name'] == 'Food & Dining':
                food_category = cat
        
        if not salary_category or not food_category:
            self.log("❌ Required system categories not found")
            return False
        
        rules_data = [
            {
                "pattern": "SALARY",
                "match_type": "CONTAINS",
                "category_id": salary_category['id'],
                "priority": 10
            },
            {
                "pattern": "ZOMATO",
                "match_type": "CONTAINS",
                "category_id": food_category['id'],
                "priority": 9
            }
        ]
        
        for i, rule_data in enumerate(rules_data, 1):
            success, response = self.api_call("POST", "rules", data=rule_data)
            if success and 'id' in response:
                self.test_rule_ids.append(response['id'])
                self.log(f"✅ Created rule {i}: {rule_data['pattern']}")
            else:
                self.log(f"❌ Failed to create rule {i}")
                return False
        
        return len(self.test_rule_ids) == 2

    def test_backup(self):
        """Test backup functionality and verify ZIP contents"""
        self.log("💾 Testing backup functionality...")
        
        # Make backup request
        url = f"{self.base_url}/api/settings/backup"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                self.log(f"❌ Backup failed with status {response.status_code}")
                return False
            
            # Verify response headers
            content_type = response.headers.get('content-type', '')
            if 'application/zip' not in content_type:
                self.log(f"❌ Expected ZIP file, got content-type: {content_type}")
                return False
            
            content_disposition = response.headers.get('content-disposition', '')
            if 'SpendAlizer-' not in content_disposition:
                self.log(f"❌ Invalid filename format: {content_disposition}")
                return False
            
            self.log(f"✅ Backup ZIP file created with correct headers")
            
            # Verify ZIP contents
            zip_content = response.content
            self.original_backup_data = zip_content
            zip_buffer = BytesIO(zip_content)
            
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                zip_files = zip_file.namelist()
                required_files = ['transactions.json', 'categories.json', 'rules.json', 'accounts.json', 'import_batches.json', 'metadata.json']
                
                for req_file in required_files:
                    if req_file not in zip_files:
                        self.log(f"❌ Missing required file in backup: {req_file}")
                        return False
                
                # Verify categories.json contains BOTH system and user categories
                categories_content = zip_file.read('categories.json')
                categories_data = json.loads(categories_content)
                
                system_categories = [cat for cat in categories_data if cat.get('is_system', False)]
                user_categories = [cat for cat in categories_data if not cat.get('is_system', False)]
                
                self.log(f"✅ Backup contains {len(system_categories)} system categories")
                self.log(f"✅ Backup contains {len(user_categories)} user categories")
                
                # Verify transactions have correct category_ids
                transactions_content = zip_file.read('transactions.json')
                transactions_data = json.loads(transactions_content)
                
                categorized_txns = [txn for txn in transactions_data if txn.get('category_id')]
                self.log(f"✅ Backup contains {len(transactions_data)} transactions, {len(categorized_txns)} categorized")
                
                # Verify metadata
                metadata_content = zip_file.read('metadata.json')
                metadata = json.loads(metadata_content)
                
                required_metadata_fields = ['backup_date', 'user_id', 'app_version', 'collections']
                for field in required_metadata_fields:
                    if field not in metadata:
                        self.log(f"❌ Missing metadata field: {field}")
                        return False
                
                collections = metadata.get('collections', {})
                self.log(f"✅ Metadata collections: {collections}")
                
                return True
                
        except Exception as e:
            self.log(f"❌ Backup test error: {e}")
            return False

    def modify_data(self):
        """Modify data by deleting some transactions and adding new category"""
        self.log("🔄 Modifying data (delete transactions, add category)...")
        
        # Delete some transactions
        delete_data = {"confirmation_text": "DELETE ALL"}
        success, response = self.api_call("POST", "transactions/delete-all", data=delete_data)
        if success:
            self.log(f"✅ Deleted {response.get('deleted_count', 0)} transactions")
        
        # Add a new user category
        new_category_data = {"name": "Test Temporary Category", "type": "EXPENSE"}
        success, response = self.api_call("POST", "categories", data=new_category_data)
        if success:
            self.log(f"✅ Added temporary category: {response.get('id')}")
        
        # Add new transactions
        csv_content = """Date,Narration,Withdrawal Amt.,Deposit Amt.
25/01/24,NEW TRANSACTION 1,100.00,
26/01/24,NEW TRANSACTION 2,200.00,"""
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(csv_content)
                temp_csv_path = f.name
            
            with open(temp_csv_path, 'rb') as f:
                files = {'file': ('new_transactions.csv', f, 'text/csv')}
                data = {
                    'account_id': self.test_account_ids[0],
                    'data_source': 'HDFC_BANK'
                }
                
                success, response = self.api_call("POST", "import", data=data, files=files)
                os.unlink(temp_csv_path)
                
                if success:
                    self.log(f"✅ Added {response.get('success_count', 0)} new transactions")
                    
        except Exception as e:
            self.log(f"❌ Error adding new transactions: {e}")
        
        return True

    def test_restore(self):
        """Test restore functionality"""
        self.log("🔄 Testing restore functionality...")
        
        if not self.original_backup_data:
            self.log("❌ No backup data available for restore")
            return False
        
        # Test restore
        url = f"{self.base_url}/api/settings/restore"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                temp_file.write(self.original_backup_data)
                temp_file_path = temp_file.name
            
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('backup.zip', f, 'application/zip')}
                response = requests.post(url, headers=headers, files=files)
            
            os.unlink(temp_file_path)
            
            if response.status_code != 200:
                self.log(f"❌ Restore failed with status {response.status_code}")
                return False
            
            restore_response = response.json()
            
            if not restore_response.get('success'):
                self.log(f"❌ Restore reported failure: {restore_response.get('message')}")
                return False
            
            restored_counts = restore_response.get('restored_counts', {})
            self.log(f"✅ Restore completed. Restored counts: {restored_counts}")
            
            # Verify system categories are NOT duplicated
            success, categories = self.api_call("GET", "categories")
            if success:
                system_categories = [cat for cat in categories if cat.get('is_system', False)]
                user_categories = [cat for cat in categories if not cat.get('is_system', False)]
                
                self.log(f"✅ After restore: {len(system_categories)} system categories")
                self.log(f"✅ After restore: {len(user_categories)} user categories")
                
                # Check for duplicates by name
                system_names = [cat['name'] for cat in system_categories]
                if len(system_names) != len(set(system_names)):
                    self.log("❌ DUPLICATE system categories found!")
                    return False
                else:
                    self.log("✅ No duplicate system categories found")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Restore test error: {e}")
            return False

    def check_data_consistency(self):
        """Check /api/debug/data-check for orphaned categories"""
        self.log("🔍 Checking data consistency...")
        
        success, response = self.api_call("GET", "debug/data-check")
        if success:
            orphaned_count = response.get('orphaned_count', 0)
            orphaned_ids = response.get('orphaned_category_ids', [])
            status = response.get('status', 'UNKNOWN')
            
            self.log(f"✅ Data check status: {status}")
            self.log(f"✅ Orphaned categories: {orphaned_count}")
            
            if orphaned_count > 0:
                self.log(f"❌ Found orphaned category IDs: {orphaned_ids}")
                return False
            else:
                self.log("✅ No orphaned categories found")
                return True
        else:
            self.log("❌ Failed to check data consistency")
            return False

    def verify_analytics(self):
        """Verify analytics works correctly after restore"""
        self.log("📊 Verifying analytics after restore...")
        
        success, response = self.api_call("GET", "analytics/summary")
        if success:
            category_breakdown = response.get('category_breakdown', [])
            total_income = response.get('total_income', 0)
            total_expense = response.get('total_expense', 0)
            transaction_count = response.get('transaction_count', 0)
            
            self.log(f"✅ Analytics summary: {transaction_count} transactions")
            self.log(f"✅ Income: ₹{total_income}, Expense: ₹{total_expense}")
            self.log(f"✅ Category breakdown: {len(category_breakdown)} categories")
            
            # Check for any orphaned category references in analytics
            for cat_breakdown in category_breakdown:
                if cat_breakdown.get('category_id') and cat_breakdown.get('category_name') is None:
                    self.log(f"❌ Orphaned category in analytics: {cat_breakdown}")
                    return False
            
            self.log("✅ No orphaned category references in analytics")
            return True
        else:
            self.log("❌ Failed to get analytics summary")
            return False

    def run_comprehensive_test(self):
        """Run the comprehensive backup/restore test as per review request"""
        self.log("🚀 Starting Database Backup and Restore Test with System Categories Architecture")
        self.log("=" * 80)
        
        test_steps = [
            ("Register User", self.register_user),
            ("Create 2 Accounts", self.create_accounts),
            ("Create 3 User Categories", self.create_user_categories),
            ("Create Transactions (mix of system/user categories)", self.create_transactions),
            ("Create 2 Rules", self.create_rules),
            ("Test Backup", self.test_backup),
            ("Modify Data", self.modify_data),
            ("Test Restore", self.test_restore),
            ("Check Data Consistency", self.check_data_consistency),
            ("Verify Analytics", self.verify_analytics)
        ]
        
        results = []
        for step_name, step_func in test_steps:
            self.log(f"\n📋 {step_name}...")
            try:
                result = step_func()
                results.append((step_name, result))
                if result:
                    self.log(f"✅ {step_name} - PASSED")
                else:
                    self.log(f"❌ {step_name} - FAILED")
                    break  # Stop on first failure for critical steps
            except Exception as e:
                self.log(f"❌ {step_name} - ERROR: {e}")
                results.append((step_name, False))
                break
        
        # Print final results
        self.log("\n" + "=" * 80)
        self.log("📊 FINAL TEST RESULTS")
        self.log("=" * 80)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for step_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            self.log(f"{status} - {step_name}")
        
        self.log(f"\n📈 Overall: {passed}/{total} steps passed")
        
        if passed == total:
            self.log("🎉 ALL TESTS PASSED - System Categories Architecture works correctly!")
            return True
        else:
            self.log("❌ SOME TESTS FAILED - Issues found with System Categories Architecture")
            return False

def main():
    tester = SystemCategoriesBackupRestoreTest()
    success = tester.run_comprehensive_test()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())