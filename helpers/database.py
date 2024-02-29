
#----------------------DB MANAGER-------------------#

import os
import aiosqlite

DATABASE_PATH = f"{os.path.realpath(os.path.dirname(__file__))}/../database/database.db"



#-----------------------PREFIX---------------------#

async def set_guild_prefix(server_id: str, prefix: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO prefixes (server_id, prefix) VALUES (?, ?)",
            (server_id, prefix),
        )
        await db.commit()








#-----------------------LOGGING--------------------------#



#----------MESSAGE LOGS WEBHOOKS-------------#
async def add_msglog_webhook(guild_id: int, webhook_url: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("INSERT INTO msglog_webhooks (guild_id, webhook_url) VALUES (?, ?)", (guild_id, webhook_url))
            await db.commit()
        except aiosqlite.IntegrityError:
            await db.execute("UPDATE msglog_webhooks SET webhook_url = ? WHERE guild_id = ?", (webhook_url, guild_id))
            await db.commit()

async def get_msglog_webhooks() -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT guild_id, webhook_url FROM msglog_webhooks")
        rows = await cursor.fetchall()
        return rows

async def remove_msglog_webhook(guild_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM msglog_webhooks WHERE guild_id = ?", (guild_id,))
        await db.commit()
    




#-----------MOD LOGS-------------------#
async def add_modlog_channel(guild_id: int, channel_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("INSERT INTO modlog_channels (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
            await db.commit()
        except aiosqlite.IntegrityError:
            await db.execute("UPDATE modlog_channels SET channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
            await db.commit()


async def get_modlog_channels() -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT guild_id, channel_id FROM modlog_channels")
        rows = await cursor.fetchall()
        return rows


async def remove_modlog_channel(guild_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM modlog_channels WHERE guild_id = ?", (guild_id,))
        await db.commit()







#--------------------BLACKLIST-------------------------#

async def get_blacklisted_users() -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT user_id, strftime('%s', created_at) FROM blacklist"
        ) as cursor:
            result = await cursor.fetchall()
            return result


async def is_blacklisted(user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT * FROM blacklist WHERE user_id=?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None


async def add_user_to_blacklist(user_id: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT INTO blacklist(user_id) VALUES (?)", (user_id,))
        await db.commit()
        rows = await db.execute("SELECT COUNT(*) FROM blacklist")
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0


async def remove_user_from_blacklist(user_id: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM blacklist WHERE user_id=?", (user_id,))
        await db.commit()
        rows = await db.execute("SELECT COUNT(*) FROM blacklist")
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0






#-----------------------WARNS-------------------------#



async def add_warn(user_id: int, server_id: int, moderator_id: int, reason: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result is not None else 1
            await db.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (
                    warn_id,
                    user_id,
                    server_id,
                    moderator_id,
                    reason,
                ),
            )
            await db.commit()
            return warn_id


async def remove_warn(warn_id: int, user_id: int, server_id: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (
                warn_id,
                user_id,
                server_id,
            ),
        )
        await db.commit()
        rows = await db.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0


async def get_warnings(user_id: int, server_id: int) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            result_list = []
            for row in result:
                result_list.append(row)
            return result_list
        
        



#---------------------------ONBOARDING------------------------------#


async def get_welcome_message(guild):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT welcome_message FROM onboarding WHERE guild_id = ?",
            (str(guild.id),),
        )
        row = await cursor.fetchone()
        if row:
            return row[0]
        else:
            return None



async def get_goodbye_message(guild):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT goodbye_message FROM onboarding WHERE guild_id = ?",
            (str(guild.id),),
        )
        row = await cursor.fetchone()
        if row:
            return row[0]
        else:
            return None
        

async def get_welcome_channel(guild):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT welcome_channel_id FROM onboarding WHERE guild_id = ?",
            (str(guild.id),),
        )
        row = await cursor.fetchone()
        if row:
            channel_id = row[0]
            welcome_channel = guild.get_channel(int(channel_id))
            return welcome_channel
        else:
            return None
        



#-----------------------AUTO ROLES-----------------------------#
async def add_auto_role(guild_id: str, role_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT auto_assign_roles FROM onboarding WHERE guild_id = ?",
            (guild_id,),
        )
        row = await cursor.fetchone()
        if row:
            auto_assign_roles = row[0]
            if auto_assign_roles:
                existing_roles = auto_assign_roles.split(",")
                if role_id in existing_roles:
                    # Role already exists in the auto assign role list
                    return
                existing_roles.append(role_id)
                updated_roles = ",".join(existing_roles)
            else:
                updated_roles = role_id
            await db.execute(
                "UPDATE onboarding SET auto_assign_roles = ? WHERE guild_id = ?",
                (updated_roles, guild_id),
            )
        else:
            await db.execute(
                "INSERT INTO onboarding (guild_id, auto_assign_roles) VALUES (?, ?)",
                (guild_id, role_id),
            )
        await db.commit()


async def remove_auto_role(guild_id: str, role_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT auto_assign_roles FROM onboarding WHERE guild_id = ?",
            (guild_id,),
        )
        row = await cursor.fetchone()
        if row:
            auto_assign_roles = row[0]
            if auto_assign_roles:
                existing_roles = auto_assign_roles.split(",")
                if role_id in existing_roles:
                    existing_roles.remove(role_id)
                    updated_roles = ",".join(existing_roles)
                    await db.execute(
                        "UPDATE onboarding SET auto_assign_roles = ? WHERE guild_id = ?",
                        (updated_roles, guild_id),
                    )
                    await db.commit()


async def get_auto_roles(guild_id: str) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT auto_assign_roles FROM onboarding WHERE guild_id = ?",
            (guild_id,),
        )
        row = await cursor.fetchone()
        if row:
            auto_assign_roles = row[0]
            if auto_assign_roles:
                return auto_assign_roles.split(",")
        return []
    





#----------------------STICKY ROLES---------------------------#
async def set_sticky_roles(user_id: str, guild_id: str, role_ids: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO sticky_roles (user_id, guild_id, role_ids) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET role_ids = ?",
            (user_id, guild_id, role_ids, role_ids),
        )
        await db.commit()

async def get_sticky_roles(user_id: str, guild_id: str) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT role_ids FROM sticky_roles WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        row = await cursor.fetchone()
        return row[0].split(",") if row else []
    




#--------------------SOCIAL INTERACTIONS-------------------------#

async def increment_interaction_count(user_id: int, target_user_id: int, interaction_type: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO interaction_counts (user_id, interaction_type, count) VALUES (?, ?, 0)",
            (target_user_id, interaction_type),
        )
        await db.execute(
            "UPDATE interaction_counts SET count = count + 1 WHERE user_id = ? AND interaction_type = ?",
            (target_user_id, interaction_type),
        )
        await db.commit()
        rows = await db.execute(
            "SELECT count FROM interaction_counts WHERE user_id = ? AND interaction_type = ?",
            (target_user_id, interaction_type),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0


async def get_interaction_count(user_id: int, interaction_type: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT count FROM interaction_counts WHERE user_id = ? AND interaction_type = ?",
            (user_id, interaction_type),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0