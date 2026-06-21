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



CREATE TABLE IF NOT EXISTS automated_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    message TEXT NOT NULL,
    interval_seconds INTEGER NOT NULL,
    next_run DATETIME NOT NULL
);



CREATE TABLE IF NOT EXISTS whitelisted_alts (
    user_id TEXT PRIMARY KEY,
    whitelisted_by TEXT NOT NULL,
    reason TEXT,
    whitelisted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);