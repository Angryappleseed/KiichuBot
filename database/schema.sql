CREATE TABLE IF NOT EXISTS `prefixes` (
  `server_id` varchar(20) NOT NULL,
  `prefix` varchar(20) NOT NULL,
  PRIMARY KEY (`server_id`)
);


CREATE TABLE IF NOT EXISTS `msglog_webhooks` (
  `guild_id` varchar(20) NOT NULL,
  `webhook_url` text NOT NULL,
  PRIMARY KEY (`guild_id`)
);

CREATE TABLE IF NOT EXISTS `modlog_channels` (
  `guild_id` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  PRIMARY KEY (`guild_id`)
);


CREATE TABLE IF NOT EXISTS `blacklist` (
  `user_id` varchar(20) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS `warns` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS `onboarding` (
  `guild_id` varchar(20) NOT NULL,
  `welcome_message` text,
  `goodbye_message` text,
  `welcome_channel_id` varchar(20),
  `auto_assign_roles` text,
  `welcome_enabled` BOOLEAN DEFAULT TRUE,
  `goodbye_enabled` BOOLEAN DEFAULT TRUE,
  `sticky_roles_enabled` BOOLEAN DEFAULT 0,
  PRIMARY KEY (`guild_id`)
);


CREATE TABLE IF NOT EXISTS `sticky_roles` (
  `user_id` varchar(20) NOT NULL,
  `guild_id` varchar(20) NOT NULL,
  `role_ids` text,
  PRIMARY KEY (`user_id`, `guild_id`)
);


CREATE TABLE IF NOT EXISTS automated_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    message TEXT NOT NULL,
    interval_seconds INTEGER NOT NULL,
    next_run DATETIME NOT NULL
);


CREATE TABLE IF NOT EXISTS youtube_last_video (
    channel_id TEXT PRIMARY KEY,
    last_video_id TEXT NOT NULL,
    publish_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS modmail_tickets (
    ticket_number INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    opened DATETIME NOT NULL DEFAULT (datetime('now')),
    closed DATETIME
);