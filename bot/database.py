import aiosqlite
from datetime import datetime, timedelta

from .config import REP_COOLDOWN_HOURS


class Database:
    def __init__(self, path):
        self.path = path
        self.db = None

    async def init(self):
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self.db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT NOT NULL,
            bio TEXT DEFAULT 'Информация не указана',
            rep INTEGER DEFAULT 0,
            warns INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            messages INTEGER DEFAULT 0,
            joined_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS rep_votes (
            giver_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            value INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(giver_id, receiver_id)
        );
        CREATE TABLE IF NOT EXISTS warn_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS mod_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            target_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER NOT NULL,
            achievement TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(user_id, achievement)
        );
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            chat_type TEXT,
            added_by INTEGER NOT NULL,
            added_at TEXT NOT NULL
        );
        """)
        await self.db.commit()

    async def close(self):
        if self.db:
            await self.db.close()

    def now(self):
        return datetime.utcnow().isoformat()

    async def _fetchone(self, sql, params=()):
        async with self.db.execute(sql, params) as cursor:
            return await cursor.fetchone()

    async def get_or_create(self, user):
        row = await self._fetchone(
            "SELECT * FROM users WHERE user_id=?", (user.id,)
        )
        if row:
            await self.db.execute(
                "UPDATE users SET username=?, first_name=? WHERE user_id=?",
                (user.username, user.first_name or "Без имени", user.id),
            )
            await self.db.commit()
            row = await self._fetchone(
                "SELECT * FROM users WHERE user_id=?", (user.id,)
            )
            return dict(row)

        await self.db.execute(
            "INSERT INTO users(user_id,username,first_name,joined_at) VALUES(?,?,?,?)",
            (user.id, user.username, user.first_name or "Без имени", self.now()),
        )
        await self.db.commit()
        return await self.get_or_create(user)

    async def get_user(self, user_id):
        row = await self._fetchone(
            "SELECT * FROM users WHERE user_id=?", (user_id,)
        )
        return dict(row) if row else None

    async def set_bio(self, user_id, bio):
        await self.db.execute(
            "UPDATE users SET bio=? WHERE user_id=?", (bio, user_id)
        )
        await self.db.commit()

    async def add_message(self, user_id, xp):
        await self.db.execute(
            "UPDATE users SET xp=xp+?, messages=messages+1 WHERE user_id=?",
            (xp, user_id),
        )
        await self.db.commit()

    async def set_rep(self, giver, receiver, value):
        row = await self._fetchone(
            "SELECT value, created_at FROM rep_votes WHERE giver_id=? AND receiver_id=?",
            (giver, receiver),
        )
        if row:
            if row["value"] == value:
                return "same"
            try:
                created = datetime.fromisoformat(row["created_at"])
            except ValueError:
                created = datetime.utcnow() - timedelta(hours=REP_COOLDOWN_HOURS + 1)
            if datetime.utcnow() - created < timedelta(hours=REP_COOLDOWN_HOURS):
                return "cooldown"
            delta = value - row["value"]
            await self.db.execute(
                "UPDATE rep_votes SET value=?, created_at=? WHERE giver_id=? AND receiver_id=?",
                (value, self.now(), giver, receiver),
            )
        else:
            delta = value
            await self.db.execute(
                "INSERT INTO rep_votes VALUES(?,?,?,?)",
                (giver, receiver, value, self.now()),
            )
        await self.db.execute(
            "UPDATE users SET rep=rep+? WHERE user_id=?", (delta, receiver)
        )
        await self.db.commit()
        return "ok"

    async def change_warns(self, user_id, delta):
        await self.db.execute(
            "UPDATE users SET warns=MAX(0,warns+?) WHERE user_id=?",
            (delta, user_id),
        )
        await self.db.commit()
        row = await self._fetchone(
            "SELECT warns FROM users WHERE user_id=?", (user_id,)
        )
        return row["warns"] if row else 0

    async def log_mod(self, chat_id, moderator, target, action, details=""):
        await self.db.execute(
            "INSERT INTO mod_log(chat_id,moderator_id,target_id,action,details,created_at) VALUES(?,?,?,?,?,?)",
            (chat_id, moderator, target, action, details, self.now()),
        )
        await self.db.commit()

    async def log_warn(self, chat_id, user_id, moderator, action, reason=""):
        await self.db.execute(
            "INSERT INTO warn_history(chat_id,user_id,moderator_id,action,reason,created_at) VALUES(?,?,?,?,?,?)",
            (chat_id, user_id, moderator, action, reason, self.now()),
        )
        await self.db.commit()

    async def award(self, user_id, name):
        try:
            await self.db.execute(
                "INSERT INTO achievements VALUES(?,?,?)",
                (user_id, name, self.now()),
            )
            await self.db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def achievements(self, user_id):
        rows = await self.db.execute_fetchall(
            "SELECT achievement FROM achievements WHERE user_id=? ORDER BY created_at",
            (user_id,),
        )
        return [r["achievement"] for r in rows]

    async def is_chat_registered(self, chat_id):
        row = await self._fetchone(
            "SELECT 1 FROM chats WHERE chat_id=?", (chat_id,)
        )
        return row is not None

    async def add_chat(self, chat_id, title, chat_type, added_by):
        try:
            await self.db.execute(
                "INSERT INTO chats(chat_id, title, chat_type, added_by, added_at) VALUES(?,?,?,?,?)",
                (chat_id, title or "", chat_type or "", added_by, self.now()),
            )
            await self.db.commit()
            return True
        except aiosqlite.IntegrityError:
            await self.db.execute(
                "UPDATE chats SET title=?, chat_type=? WHERE chat_id=?",
                (title or "", chat_type or "", chat_id),
            )
            await self.db.commit()
            return False

    async def remove_chat(self, chat_id):
        cursor = await self.db.execute(
            "DELETE FROM chats WHERE chat_id=?", (chat_id,)
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def list_chats(self, added_by=None):
        if added_by is not None:
            rows = await self.db.execute_fetchall(
                "SELECT * FROM chats WHERE added_by=? ORDER BY added_at DESC",
                (added_by,),
            )
        else:
            rows = await self.db.execute_fetchall(
                "SELECT * FROM chats ORDER BY added_at DESC"
            )
        return [dict(r) for r in rows]

    async def get_chat(self, chat_id):
        row = await self._fetchone(
            "SELECT * FROM chats WHERE chat_id=?", (chat_id,)
        )
        return dict(row) if row else None
