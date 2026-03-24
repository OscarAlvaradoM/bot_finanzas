import unittest

from services.validators import is_expected_reply, validate_amount_text, validate_required_name
from types import SimpleNamespace


class ValidatorsTests(unittest.TestCase):
    def test_validate_amount_text_parsea_formato_moneda(self):
        self.assertEqual(validate_amount_text("$1,250.50"), 1250.50)

    def test_validate_required_name_rechaza_vacio(self):
        with self.assertRaises(ValueError):
            validate_required_name("   ")

    def test_is_expected_reply_acepta_respuesta_correcta(self):
        message = SimpleNamespace(reply_to_message=SimpleNamespace(message_id=10))
        self.assertTrue(is_expected_reply(message, 10))

    def test_is_expected_reply_rechaza_reply_a_otro_mensaje(self):
        message = SimpleNamespace(reply_to_message=SimpleNamespace(message_id=20))
        self.assertFalse(is_expected_reply(message, 10))
