import aiosqlite
from datetime import datetime


class Database:
    def __init__(self, db_path="bot.db"):
        self.db_path = db_path

    async def create_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    qk_code TEXT UNIQUE,
                    bananas INTEGER DEFAULT 0,
                    stars INTEGER DEFAULT 0,
                    cakes INTEGER DEFAULT 0,
                    startL INTEGER DEFAULT 0,
                    startB INTEGER DEFAULT 0,
                    registration_date TEXT
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    amount INTEGER,
                    currency TEXT,
                    activations INTEGER DEFAULT 0,
                    max_activations INTEGER,
                    creator_id INTEGER,
                    created_date TEXT,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS check_activations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_code TEXT,
                    user_id INTEGER,
                    activation_date TEXT,
                    UNIQUE(check_code, user_id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    transaction_id TEXT UNIQUE,
                    status TEXT,
                    payment_type TEXT,
                    created_date TEXT
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    withdrawal_id TEXT UNIQUE,
                    status TEXT DEFAULT 'pending',
                    created_date TEXT
                )
            ''')
            await db.commit()

    async def user_exists(self, user_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
            )
            result = await cursor.fetchone()
            return result is not None

    async def add_user(self, user_id, username, qk_code):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''INSERT INTO users (user_id, username, qk_code, registration_date) 
                   VALUES (?, ?, ?, ?)''',
                (user_id, username, qk_code, datetime.now().isoformat())
            )
            await db.commit()

    async def get_user(self, user_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'username': row[1],
                    'qk_code': row[2],
                    'bananas': row[3],
                    'stars': row[4],
                    'cakes': row[5],
                    'startL': row[6],
                    'startB': row[7],
                    'registration_date': row[8]
                }
            return None

    async def get_all_users(self):
        """Получает всех пользователей для админа"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, username FROM users ORDER BY user_id"
            )
            rows = await cursor.fetchall()
            return [{'user_id': row[0], 'username': row[1]} for row in rows]

    async def update_user_currency(self, user_id, currency, amount):
        """Устанавливает новое значение валюты пользователю"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE users SET {currency} = ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()

    async def qk_exists(self, qk_code):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT qk_code FROM users WHERE qk_code = ?", (qk_code,)
            )
            result = await cursor.fetchone()
            return result is not None

    async def create_check(self, code, amount, currency, max_activations, creator_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''INSERT INTO checks (code, amount, currency, max_activations, creator_id, created_date) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (code, amount, currency, max_activations, creator_id, datetime.now().isoformat())
            )
            await db.commit()

    async def get_check(self, code):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM checks WHERE code = ?", (code,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'code': row[1],
                    'amount': row[2],
                    'currency': row[3],
                    'activations': row[4],
                    'max_activations': row[5],
                    'creator_id': row[6],
                    'created_date': row[7],
                    'is_active': row[8]
                }
            return None

    async def check_user_activated(self, check_code, user_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM check_activations WHERE check_code = ? AND user_id = ?",
                (check_code, user_id)
            )
            result = await cursor.fetchone()
            return result is not None

    async def activate_check(self, check_code, user_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''INSERT INTO check_activations (check_code, user_id, activation_date) 
                   VALUES (?, ?, ?)''',
                (check_code, user_id, datetime.now().isoformat())
            )

            await db.execute(
                "UPDATE checks SET activations = activations + 1 WHERE code = ?",
                (check_code,)
            )

            await db.commit()

    async def add_currency(self, user_id, currency, amount):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE users SET {currency} = {currency} + ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()

    async def subtract_stars(self, user_id, amount):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET startL = startL - ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()

    async def add_stars_user(self, user_id, amount):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET startL = startL + ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()

    async def add_stars_bot(self, amount):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET startB = startB + ? WHERE user_id = ?",
                (amount, 2200183708)
            )
            await db.commit()

    async def add_transaction(self, user_id, amount, transaction_id, payment_type):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''INSERT INTO transactions (user_id, amount, transaction_id, status, payment_type, created_date) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, amount, transaction_id, "pending", payment_type, datetime.now().isoformat())
            )
            await db.commit()

    async def update_transaction_status(self, transaction_id, status):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE transactions SET status = ? WHERE transaction_id = ?",
                (status, transaction_id)
            )
            await db.commit()

    async def get_transaction(self, transaction_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'amount': row[2],
                    'transaction_id': row[3],
                    'status': row[4],
                    'payment_type': row[5],
                    'created_date': row[6]
                }
            return None

    async def create_withdrawal(self, user_id, amount, withdrawal_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''INSERT INTO withdrawals (user_id, amount, withdrawal_id, created_date) 
                   VALUES (?, ?, ?, ?)''',
                (user_id, amount, withdrawal_id, datetime.now().isoformat())
            )
            await db.commit()

    async def get_withdrawal(self, withdrawal_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM withdrawals WHERE withdrawal_id = ?", (withdrawal_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'amount': row[2],
                    'withdrawal_id': row[3],
                    'status': row[4],
                    'created_date': row[5]
                }
            return None

    async def update_withdrawal_status(self, withdrawal_id, status):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE withdrawals SET status = ? WHERE withdrawal_id = ?",
                (status, withdrawal_id)
            )
            await db.commit()

    async def deactivate_check(self, check_code):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE checks SET is_active = 0 WHERE code = ?",
                (check_code,)
            )
            await db.commit()

    async def get_stats(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT SUM(bananas), SUM(stars), SUM(cakes), SUM(startL), SUM(startB) FROM users"
            )
            totals = await cursor.fetchone()

            cursor = await db.execute("SELECT COUNT(*) FROM checks")
            total_checks = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT SUM(activations) FROM checks")
            total_activations = (await cursor.fetchone())[0] or 0

            cursor = await db.execute("SELECT COUNT(*) FROM withdrawals")
            total_withdrawals = (await cursor.fetchone())[0]

            return {
                'total_users': total_users,
                'total_bananas': totals[0] or 0,
                'total_stars': totals[1] or 0,
                'total_cakes': totals[2] or 0,
                'total_startL': totals[3] or 0,
                'total_startB': totals[4] or 0,
                'total_checks': total_checks,
                'total_activations': total_activations,
                'total_withdrawals': total_withdrawals
            }