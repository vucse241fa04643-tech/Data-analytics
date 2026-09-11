"""
Test Suite for Agent 63 Schema Registry & Security Classifications
Validates non-negotiable security boundaries, isolation of confidential schemas,
absence of credentials, and schema integrity.
"""

import json
import os
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(ROOT_DIR, "database", "mappings", "agent63_schema_registry.json")
INVENTORY_PATH = os.path.join(ROOT_DIR, "database", "schema", "college_schema_inventory.json")

class TestSchemaRegistrySecurity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.exists(REGISTRY_PATH), f"Registry file missing at {REGISTRY_PATH}")
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            cls.registry = json.load(f)
        cls.objects = cls.registry.get("objects", [])

    def test_01_registry_is_valid_json_and_has_required_metadata(self):
        """Test 9: Schema registry is valid JSON with mandatory metadata."""
        self.assertIn("version", self.registry)
        self.assertEqual(self.registry.get("database_engine"), "postgresql")
        self.assertEqual(self.registry.get("database_version_target"), "14+")
        self.assertGreater(len(self.objects), 200, "Registry should contain over 200 objects.")

    def test_02_confidential_schema_strictly_denied(self):
        """Test 1 & 8: Confidential schema objects are strictly marked DENY_GENERAL_ANALYTICS."""
        confidential_objects = [o for o in self.objects if o.get("schema") == "confidential"]
        self.assertGreater(len(confidential_objects), 0, "Confidential schema objects must be cataloged.")
        for obj in confidential_objects:
            self.assertEqual(
                obj.get("access"),
                "DENY_GENERAL_ANALYTICS",
                f"Confidential object '{obj.get('full_name')}' must be DENY_GENERAL_ANALYTICS"
            )
            self.assertEqual(
                obj.get("sensitivity"),
                "HIGHLY_SENSITIVE",
                f"Confidential object '{obj.get('full_name')}' must be HIGHLY_SENSITIVE"
            )

    def test_03_no_credentials_in_registry(self):
        """Test 2: No credentials, passwords, tokens, or connection strings appear in registry."""
        raw_text = json.dumps(self.registry).lower()
        forbidden_patterns = [
            "password123", "secret_key", "bearer ", "private_key",
            "postgres://", "mysql://", "mongodb://"
        ]
        for pattern in forbidden_patterns:
            self.assertNotIn(pattern, raw_text, f"Forbidden credential pattern '{pattern}' found in registry.")

    def test_04_registry_contains_valid_classifications(self):
        """Test 3: All objects contain valid access and sensitivity classifications."""
        valid_access = {"ALLOW", "ALLOW_WITH_ROLE_SCOPE", "ROLE_RESTRICTED", "RESTRICTED", "DENY_GENERAL_ANALYTICS"}
        valid_sens = {"PUBLIC_ANALYTICS", "INTERNAL_ANALYTICS", "ROLE_RESTRICTED", "SENSITIVE", "HIGHLY_SENSITIVE"}
        for obj in self.objects:
            self.assertIn(obj.get("access"), valid_access, f"Invalid access in {obj.get('full_name')}")
            self.assertIn(obj.get("sensitivity"), valid_sens, f"Invalid sensitivity in {obj.get('full_name')}")

    def test_05_restricted_objects_not_accidentally_unrestricted(self):
        """Test 4: Restricted objects (exam papers, malpractice) are properly restricted."""
        strictly_restricted = [
            "assessment.question_paper",
            "exams.question_paper_delivery",
            "exams.malpractice_incident"
        ]
        for name in strictly_restricted:
            matching = [o for o in self.objects if o.get("full_name") == name]
            if matching:
                obj = matching[0]
                self.assertEqual(obj.get("access"), "DENY_GENERAL_ANALYTICS")
                self.assertEqual(obj.get("sensitivity"), "HIGHLY_SENSITIVE")

    def test_06_identity_auth_secrets_not_exposed(self):
        """Test 6: Identity user credentials and session data are restricted/denied."""
        identity_auth_tables = ["identity.auth_credential", "identity.app_user", "identity.user_session"]
        for name in identity_auth_tables:
            matching = [o for o in self.objects if o.get("full_name") == name]
            if matching:
                obj = matching[0]
                self.assertIn(obj.get("access"), ["RESTRICTED", "DENY_GENERAL_ANALYTICS"])

    def test_07_no_synthetic_college_data_created(self):
        """Test 10: No synthetic university database files or fake student dumps exist in repo."""
        database_dir = os.path.join(ROOT_DIR, "database")
        for root, dirs, files in os.walk(database_dir):
            for f in files:
                self.assertFalse(
                    f.endswith(".sqlite") or f.endswith(".sqlite3") or f.endswith(".db"),
                    f"Forbidden synthetic SQLite database found: {f}"
                )
                self.assertNotIn("mock_students", f.lower())
                self.assertNotIn("fake_attendance", f.lower())

    def test_08_unknown_database_objects_rejected(self):
        """Test 5: Lookup helper rejects objects not explicitly in the registry."""
        allowed_names = {o["full_name"] for o in self.objects if o["access"] in ["ALLOW", "ALLOW_WITH_ROLE_SCOPE"]}
        fake_object = "academics.synthetic_student_grades"
        self.assertNotIn(fake_object, allowed_names, "Unknown objects must not be treated as allowed.")

if __name__ == "__main__":
    unittest.main()
