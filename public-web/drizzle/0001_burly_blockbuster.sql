CREATE TABLE `excel_references` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`filename` text NOT NULL,
	`sha256` text NOT NULL,
	`size` integer NOT NULL,
	`imported_at` integer NOT NULL,
	`imported_by` text NOT NULL,
	`source_modified` text,
	`row_count` integer NOT NULL,
	`tasks` text NOT NULL,
	`file_base64` text NOT NULL,
	FOREIGN KEY (`imported_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `excel_references_sha256_unique` ON `excel_references` (`sha256`);