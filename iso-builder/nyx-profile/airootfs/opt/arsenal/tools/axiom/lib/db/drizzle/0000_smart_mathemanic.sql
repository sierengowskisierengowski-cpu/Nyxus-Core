CREATE TABLE IF NOT EXISTS `chat_messages` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`session_id` integer NOT NULL,
	`role` text NOT NULL,
	`content` text NOT NULL,
	`action_type` text,
	`action_data` text,
	`created_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) NOT NULL,
	FOREIGN KEY (`session_id`) REFERENCES `chat_sessions`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `chat_sessions` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`title` text DEFAULT 'New Chat' NOT NULL,
	`created_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) NOT NULL,
	`updated_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `scheduled_tasks` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text NOT NULL,
	`command` text NOT NULL,
	`schedule` text NOT NULL,
	`schedule_label` text,
	`enabled` integer DEFAULT true NOT NULL,
	`last_run_at` text,
	`last_run_status` text,
	`next_run_at` text,
	`created_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `knowledge_notes` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`title` text NOT NULL,
	`content` text DEFAULT '' NOT NULL,
	`pinned` integer DEFAULT false NOT NULL,
	`created_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) NOT NULL,
	`updated_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `activity_log` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`type` text NOT NULL,
	`description` text NOT NULL,
	`detail` text,
	`files_affected` text DEFAULT '[]' NOT NULL,
	`undoable` integer DEFAULT false NOT NULL,
	`undone` integer DEFAULT false NOT NULL,
	`undo_data` text,
	`created_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `quick_actions` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`label` text NOT NULL,
	`command` text NOT NULL,
	`icon` text,
	`color` text,
	`order` integer DEFAULT 0 NOT NULL,
	`created_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `settings` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`hotkey` text DEFAULT 'CommandOrControl+Shift+Space' NOT NULL,
	`ai_mode` text DEFAULT 'cloud' NOT NULL,
	`ai_model` text DEFAULT 'gpt-4o-mini' NOT NULL,
	`cloud_api_key` text,
	`cloud_base_url` text,
	`ollama_base_url` text DEFAULT 'http://localhost:11434' NOT NULL,
	`theme` text DEFAULT 'dark' NOT NULL,
	`launch_at_login` integer DEFAULT false NOT NULL,
	`start_minimized` integer DEFAULT false NOT NULL,
	`dismiss_on_blur` integer DEFAULT true NOT NULL,
	`notify_on_schedule` integer DEFAULT true NOT NULL,
	`notify_on_error` integer DEFAULT true NOT NULL,
	`window_width` integer DEFAULT 780 NOT NULL,
	`window_height` integer DEFAULT 640 NOT NULL,
	`onboarding_completed` integer DEFAULT false NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `allowed_paths` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`path` text NOT NULL,
	`label` text,
	`created_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS `allowed_paths_path_unique` ON `allowed_paths` (`path`);
