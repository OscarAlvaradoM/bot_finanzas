import pathlib
import sys
import types
from types import SimpleNamespace

from domain.schema import SHEET_HEADERS


ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "Src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def ensure_stub_modules():
    if "dotenv" not in sys.modules:
        dotenv = types.ModuleType("dotenv")

        def load_dotenv(*args, **kwargs):
            return False

        dotenv.load_dotenv = load_dotenv
        sys.modules["dotenv"] = dotenv

    if "telegram" not in sys.modules:
        telegram = types.ModuleType("telegram")

        class Update:
            pass

        class InlineKeyboardButton:
            def __init__(self, text, callback_data=None):
                self.text = text
                self.callback_data = callback_data

        class InlineKeyboardMarkup:
            def __init__(self, keyboard):
                self.keyboard = keyboard

        telegram.Update = Update
        telegram.InlineKeyboardButton = InlineKeyboardButton
        telegram.InlineKeyboardMarkup = InlineKeyboardMarkup
        sys.modules["telegram"] = telegram

    if "telegram.ext" not in sys.modules:
        telegram_ext = types.ModuleType("telegram.ext")

        class ContextTypes:
            DEFAULT_TYPE = object

        class ConversationHandler:
            END = -1

        telegram_ext.ContextTypes = ContextTypes
        telegram_ext.ConversationHandler = ConversationHandler
        sys.modules["telegram.ext"] = telegram_ext

    if "gspread" not in sys.modules:
        gspread = types.ModuleType("gspread")

        def authorize(client):
            return client

        gspread.authorize = authorize
        sys.modules["gspread"] = gspread

    if "oauth2client" not in sys.modules:
        oauth2client = types.ModuleType("oauth2client")
        sys.modules["oauth2client"] = oauth2client

    if "oauth2client.service_account" not in sys.modules:
        service_account = types.ModuleType("oauth2client.service_account")

        class ServiceAccountCredentials:
            @staticmethod
            def from_json_keyfile_name(path, scope):
                return SimpleNamespace(path=path, scope=scope)

        service_account.ServiceAccountCredentials = ServiceAccountCredentials
        sys.modules["oauth2client.service_account"] = service_account


ensure_stub_modules()


class FakeBot:
    def __init__(self):
        self.sent_messages = []

    async def send_message(self, **kwargs):
        self.sent_messages.append(kwargs)
        return SimpleNamespace(message_id=len(self.sent_messages))


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append({"text": text, **kwargs})


class FakeCallbackQuery:
    def __init__(self, data=None):
        self.data = data
        self.answered = False
        self.edits = []

    async def answer(self):
        self.answered = True

    async def edit_message_text(self, text, **kwargs):
        self.edits.append({"text": text, **kwargs})


class FakeUpdate:
    def __init__(self, *, message=None, callback_query=None, chat_id=12345):
        self.message = message
        self.callback_query = callback_query
        self.effective_chat = SimpleNamespace(id=chat_id)


class FakeContext:
    def __init__(self, *, bot=None, user_data=None):
        self.bot = bot or FakeBot()
        self.user_data = user_data or {}


class FakeSheet:
    def __init__(self, *, records=None, headers=None):
        self.records = records or []
        self.rows = []
        self.headers = headers or SHEET_HEADERS[:-1]

    def get_all_records(self):
        return self.records

    def append_row(self, row):
        self.rows.append(row)

    def row_values(self, index):
        if index == 1:
            return self.headers
        return []

    def update_cell(self, row, col, value):
        if row != 1:
            return
        while len(self.headers) < col:
            self.headers.append("")
        self.headers[col - 1] = value
