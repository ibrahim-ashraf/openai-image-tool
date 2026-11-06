import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from image_tool import config


class MemoryCredentialStore:
    priority = 1

    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        self.values.pop((service, username), None)


class APIKeyConfigTests(unittest.TestCase):

    def setUp(self):
        self.store = MemoryCredentialStore()
        self.keyring_patch = patch.object(
            config.keyring,
            "get_keyring",
            return_value=self.store
        )
        self.keyring_patch.start()
        self.addCleanup(self.keyring_patch.stop)

        self.environment_patch = patch.dict(
            os.environ,
            {},
            clear=True
        )
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)

        self.openai_patch = patch.object(
            config,
            "OpenAI",
            side_effect=lambda api_key: SimpleNamespace(api_key=api_key)
        )
        self.openai_patch.start()
        self.addCleanup(self.openai_patch.stop)

        self.previous_api_key = config.API_KEY
        self.previous_client = config.client
        self.addCleanup(self.restore_config)

    def restore_config(self):
        config.API_KEY = self.previous_api_key
        config.client = self.previous_client

    def test_saves_and_loads_key_from_credential_store(self):
        config.set_api_key("test-key")

        self.assertEqual(
            self.store.get_password(
                config.KEYRING_SERVICE,
                config.KEYRING_USERNAME
            ),
            "test-key"
        )
        self.assertTrue(config.has_api_key())
        self.assertEqual(config.initialize_client().api_key, "test-key")

    def test_saved_key_takes_precedence_over_environment(self):
        self.store.set_password(
            config.KEYRING_SERVICE,
            config.KEYRING_USERNAME,
            "stored-key"
        )
        os.environ["OPENAI_API_KEY"] = "environment-key"

        self.assertEqual(config.get_api_key(), "stored-key")

    def test_environment_key_is_supported_as_advanced_fallback(self):
        os.environ["OPENAI_API_KEY"] = "environment-key"

        self.assertEqual(config.get_api_key(), "environment-key")
        self.assertEqual(config.initialize_client().api_key, "environment-key")

    def test_removing_key_clears_credential_and_client(self):
        config.set_api_key("test-key")

        config.clear_api_key()

        self.assertIsNone(
            self.store.get_password(
                config.KEYRING_SERVICE,
                config.KEYRING_USERNAME
            )
        )
        self.assertIsNone(config.client)

    def test_blank_key_is_rejected(self):
        with self.assertRaises(ValueError):
            config.set_api_key("  ")


if __name__ == "__main__":
    unittest.main()
