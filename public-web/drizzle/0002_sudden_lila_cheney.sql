CREATE TABLE `reconciliation_runs` (
	`id` text PRIMARY KEY NOT NULL,
	`reference_id` integer NOT NULL,
	`actor` text NOT NULL,
	`created` integer NOT NULL,
	`report` text NOT NULL,
	`backup` text NOT NULL,
	`guard` integer NOT NULL,
	`capability` text,
	FOREIGN KEY (`reference_id`) REFERENCES `excel_references`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`actor`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "reconciliation_snapshot" CHECK("reconciliation_runs"."guard" = 1)
);
--> statement-breakpoint
CREATE UNIQUE INDEX `reconciliation_runs_capability_unique` ON `reconciliation_runs` (`capability`);