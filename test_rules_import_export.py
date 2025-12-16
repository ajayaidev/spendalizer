#!/usr/bin/env python3
"""
Focused test script for Rule Import/Export functionality
"""
import requests
import json
from datetime import datetime

class RuleImportExportTester:
    def __init__(self, base_url="https://money-insight-28.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.test_categories = []
        
    def register_and_login(self):
        """Register a new test user and get auth token"""
        test_user_data = {
            "email": f"rule_test_{datetime.now().strftime('%H%M%S')}@example.com",
            "name": "Rule Test User",
            "password": "TestPass123!"
        }
        
        url = f"{self.base_url}/api/auth/register"
        response = requests.post(url, json=test_user_data)
        
        if response.status_code == 200:
            data = response.json()
            self.token = data['token']
            self.user_id = data['user']['id']
            print(f"✅ Registered user: {data['user']['email']}")
            return True
        else:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return False
    
    def get_headers(self):
        """Get headers with auth token"""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def get_categories(self):
        """Get available categories"""
        url = f"{self.base_url}/api/categories"
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            self.test_categories = response.json()[:3]  # Use first 3 categories
            print(f"✅ Found {len(self.test_categories)} categories for testing")
            return True
        else:
            print(f"❌ Failed to get categories: {response.status_code}")
            return False
    
    def create_test_rules(self):
        """Create test rules for export/import testing"""
        if not self.test_categories:
            print("❌ No categories available")
            return False
            
        test_rules = [
            {
                "pattern": "ZOMATO",
                "match_type": "CONTAINS",
                "category_id": self.test_categories[0]['id'],
                "priority": 10
            },
            {
                "pattern": "SWIGGY", 
                "match_type": "CONTAINS",
                "category_id": self.test_categories[1]['id'],
                "priority": 9
            },
            {
                "pattern": "ACH C-",
                "match_type": "STARTS_WITH", 
                "category_id": self.test_categories[2]['id'] if len(self.test_categories) > 2 else self.test_categories[0]['id'],
                "priority": 8
            }
        ]
        
        created_count = 0
        for rule_data in test_rules:
            url = f"{self.base_url}/api/rules"
            response = requests.post(url, json=rule_data, headers=self.get_headers())
            
            if response.status_code == 200:
                created_count += 1
                print(f"✅ Created rule: {rule_data['pattern']}")
            else:
                print(f"❌ Failed to create rule {rule_data['pattern']}: {response.status_code}")
        
        print(f"Created {created_count} test rules")
        return created_count > 0
    
    def test_export_rules(self):
        """Test rule export functionality"""
        print("\n🔍 Testing Rule Export...")
        url = f"{self.base_url}/api/rules/export"
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code != 200:
            print(f"❌ Export failed: {response.status_code} - {response.text}")
            return False, []
        
        rules = response.json()
        print(f"✅ Exported {len(rules)} rules")
        
        # Verify each rule has required fields
        for i, rule in enumerate(rules):
            required_fields = ['pattern', 'match_type', 'category_id', 'priority']
            missing_fields = [field for field in required_fields if field not in rule]
            
            if missing_fields:
                print(f"❌ Rule {i+1} missing fields: {missing_fields}")
                return False, []
            
            if 'category_name' not in rule:
                print(f"❌ Rule {i+1} missing category_name field")
                return False, []
            
            print(f"   Rule {i+1}: {rule['pattern']} ({rule['match_type']}) -> {rule['category_name']}")
        
        print("✅ All exported rules have required fields including category_name")
        return True, rules
    
    def test_import_valid_rules(self, exported_rules):
        """Test importing valid rules"""
        print("\n🔍 Testing Rule Import with Valid Data...")
        
        # First delete all existing rules
        url = f"{self.base_url}/api/rules"
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            existing_rules = response.json()
            for rule in existing_rules:
                delete_url = f"{self.base_url}/api/rules/{rule['id']}"
                requests.delete(delete_url, headers=self.get_headers())
            print(f"   Deleted {len(existing_rules)} existing rules")
        
        # Import the exported rules
        import_data = {"rules": exported_rules}
        url = f"{self.base_url}/api/rules/import"
        response = requests.post(url, json=import_data, headers=self.get_headers())
        
        if response.status_code != 200:
            print(f"❌ Import failed: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        imported_count = result.get('imported_count', 0)
        skipped_count = result.get('skipped_count', 0)
        
        print(f"   Import result: {imported_count} imported, {skipped_count} skipped")
        
        # Verify rules were imported
        url = f"{self.base_url}/api/rules"
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            new_rules = response.json()
            if len(new_rules) == imported_count:
                print(f"✅ Successfully imported {imported_count} rules")
                return True
            else:
                print(f"❌ Rule count mismatch: expected {imported_count}, got {len(new_rules)}")
                return False
        else:
            print(f"❌ Failed to verify imported rules: {response.status_code}")
            return False
    
    def test_import_invalid_category(self):
        """Test importing rules with invalid category_id"""
        print("\n🔍 Testing Rule Import with Invalid Category...")
        
        invalid_rules = [{
            "pattern": "INVALID_TEST",
            "match_type": "CONTAINS",
            "category_id": "non-existent-category-id-12345",
            "priority": 10
        }]
        
        import_data = {"rules": invalid_rules}
        url = f"{self.base_url}/api/rules/import"
        response = requests.post(url, json=import_data, headers=self.get_headers())
        
        if response.status_code != 200:
            print(f"❌ Import failed: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        imported_count = result.get('imported_count', 0)
        skipped_count = result.get('skipped_count', 0)
        
        if imported_count == 0 and skipped_count == 1:
            print(f"✅ Correctly skipped rule with invalid category")
            return True
        else:
            print(f"❌ Expected 0 imported, 1 skipped. Got {imported_count} imported, {skipped_count} skipped")
            return False
    
    def test_import_empty_array(self):
        """Test importing empty rules array"""
        print("\n🔍 Testing Rule Import with Empty Array...")
        
        import_data = {"rules": []}
        url = f"{self.base_url}/api/rules/import"
        response = requests.post(url, json=import_data, headers=self.get_headers())
        
        if response.status_code != 200:
            print(f"❌ Import failed: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        imported_count = result.get('imported_count', 0)
        skipped_count = result.get('skipped_count', 0)
        
        if imported_count == 0 and skipped_count == 0:
            print(f"✅ Correctly handled empty rules array")
            return True
        else:
            print(f"❌ Expected 0 imported, 0 skipped. Got {imported_count} imported, {skipped_count} skipped")
            return False
    
    def run_all_tests(self):
        """Run all rule import/export tests"""
        print("🚀 Starting Rule Import/Export Tests")
        print("=" * 50)
        
        # Setup
        if not self.register_and_login():
            return False
        
        if not self.get_categories():
            return False
        
        if not self.create_test_rules():
            return False
        
        # Test export
        export_success, exported_rules = self.test_export_rules()
        if not export_success:
            return False
        
        # Test import scenarios
        tests = [
            ("Import Valid Rules", lambda: self.test_import_valid_rules(exported_rules)),
            ("Import Invalid Category", self.test_import_invalid_category),
            ("Import Empty Array", self.test_import_empty_array)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    print(f"✅ {test_name} - PASSED")
                else:
                    print(f"❌ {test_name} - FAILED")
            except Exception as e:
                print(f"❌ {test_name} - ERROR: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results) + 1  # +1 for export test
        
        print(f"✅ Export Rules - PASSED")
        for test_name, result in results:
            status = "PASSED" if result else "FAILED"
            emoji = "✅" if result else "❌"
            print(f"{emoji} {test_name} - {status}")
        
        print(f"\n📈 Overall: {passed + 1}/{total} tests passed")
        
        if passed + 1 == total:
            print("\n🎉 All rule import/export tests passed!")
            return True
        else:
            print(f"\n❌ {total - passed - 1} tests failed")
            return False

if __name__ == "__main__":
    tester = RuleImportExportTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)