import asyncio
import unittest
from unittest.mock import AsyncMock, patch
import json

# Import delle classi e dei moduli corretti
from classi.settings import Settings
from classi.setup import Step, GroupSetup, StepType
from classi.utente import Utente, UtenteDAO
from classi.chat import Chat, ChatType, ChatDAO
from classi.roles import Role, RoleDAO, RolesType
from classi.joinRequst import JoinRequest, JoinRequestDAO, JoinRequestStatus
from classi.message import Message, MessageDAO
import DB as db_manager  # Corretto per puntare al modulo DB corretto

class TestBotApp(unittest.TestCase):

    def run(self, result=None):
        test_method_name = self._testMethodName
        print(f"[-] Esecuzione test: {test_method_name}...", end=" ")
        
        # Esegue il test e cattura il risultato
        original_errors_len = len(result.errors) if result else 0
        original_failures_len = len(result.failures) if result else 0
        
        super().run(result)
        
        has_failed = (result and (len(result.errors) > original_errors_len or len(result.failures) > original_failures_len))
        if has_failed:
            print("\033[91m[FALLITO]\033[0m")
        else:
            print("\033[92m[SUCCESSO]\033[0m")

    def test_settings_conversion(self):
        s = Settings()
        s.set("lang", "it")
        self.assertEqual(s.get("lang"), "it")
        
        json_str = s.toJSON()
        s2 = Settings.fromJSON(json_str)
        self.assertEqual(s2.get("lang"), "it")

    def test_step_validation(self):
        step = Step(key="age", type="Message", question="How old are you?", question_type="Message")
        self.assertEqual(step.key, "age")
        
        with self.assertRaises(Exception):
            Step(key="photo", type="Photo", question="Send photo", question_type="Photo", media=None)

    def test_group_setup(self):
        step1 = Step(key="q1", type="Message", question="Q1?", question_type="Message")
        step2 = Step(key="q2", type="Message", question="Q2?", question_type="Message")
        setup = GroupSetup(steps=[step1, step2])
        
        self.assertTrue(setup.hasNext())
        self.assertEqual(setup.getCurrent().key, "q1")
        next_step = setup.getNext()
        self.assertEqual(next_step.key, "q2")
        self.assertFalse(setup.hasNext())

    def test_utente_model(self):
        u = Utente(id=123, name="Mario", surname="Rossi", username="mario_rossi")
        self.assertEqual(str(u), "Mario (123) - mario_rossi")

    def test_chat_model(self):
        c = Chat(id=456, type=ChatType.Group, name="Test Group")
        self.assertEqual(str(c), "Test Group (456) - G")
        
        with self.assertRaises(Exception):
            Chat(id=789, type="X", name="Invalid Chat")

    def test_role_model(self):
        # Corretto parametro grou_id come definito in roles.py
        r = Role(user_id=123, grup_id=456, role=RolesType.Administrator)
        self.assertEqual(r.role, "A")
        
        with self.assertRaises(Exception):
            Role(user_id=123, grup_id=456, role="Z")

    def test_join_request_model(self):
        jr = JoinRequest(user_id=123, chat_id=456, status=JoinRequestStatus.Pending)
        self.assertEqual(jr.status, "P")
        
        with self.assertRaises(Exception):
            JoinRequest(user_id=123, chat_id=456, status="X")


class TestDAOsAsync(unittest.IsolatedAsyncioTestCase):

    def run(self, result=None):
        test_method_name = self._testMethodName
        print(f"[-] Esecuzione test async: {test_method_name}...", end=" ")
        
        original_errors_len = len(result.errors) if result else 0
        original_failures_len = len(result.failures) if result else 0
        
        super().run(result)
        
        has_failed = (result and (len(result.errors) > original_errors_len or len(result.failures) > original_failures_len))
        if has_failed:
            print("\033[91m[FALLITO]\033[0m")
        else:
            print("\033[92m[SUCCESSO]\033[0m")

    @patch('DB.db_manager.execute')
    async def test_utente_dao_get(self, mock_execute):
        mock_execute.return_value = [{
            'id': 123,
            'nome': 'Mario',
            'cogn': 'Rossi',
            'username': 'mario',
            'settings': '{"theme": "dark"}'
        }]
        
        user = await UtenteDAO.get_by_id(123)
        self.assertIsNotNone(user)
        self.assertEqual(user.name, 'Mario')
        self.assertEqual(user.settings.get('theme'), 'dark')

    @patch('DB.db_manager.perform')
    async def test_utente_dao_save(self, mock_perform):
        mock_perform.return_value = 1
        user = Utente(id=123, name="Mario")
        res = await UtenteDAO.save(user)
        self.assertTrue(res)

    @patch('DB.db_manager.execute')
    async def test_chat_dao_get(self, mock_execute):
        mock_execute.return_value = [{
            'id': 456,
            'tipo': 'G',
            'nome': 'Gruppo Test',
            'setup': '[]',
            'settings': '{}'
        }]
        chat = await ChatDAO.get_by_id(456)
        self.assertIsNotNone(chat)
        self.assertEqual(chat.name, 'Gruppo Test')
        self.assertEqual(chat.type, ChatType.Group)

    @patch('DB.db_manager.execute')
    async def test_role_dao_get(self, mock_execute):
        mock_execute.return_value = [{
            'uten': 123,
            'chat': 456,
            'role': 'A'
        }]
        roles = await RoleDAO.get_by_group_id(456)
        self.assertIsNotNone(roles)
        self.assertIn(123, roles)
        self.assertEqual(roles[123].role, 'A')

    @patch('DB.db_manager.perform')
    async def test_join_request_create(self, mock_perform):
        mock_perform.return_value = 10
        jr = JoinRequest(user_id=123, chat_id=456)
        req_id = await JoinRequestDAO.create(jr)
        self.assertEqual(req_id, 10)


if __name__ == '__main__':
    print("=== AVVIO DELLA SUITE DI TEST ===")
    unittest.main(verbosity=0)