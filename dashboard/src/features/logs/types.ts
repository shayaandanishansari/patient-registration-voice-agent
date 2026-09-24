import type { components } from "@/types/api";

export type LogEntry = components["schemas"]["LogOut"];

export const LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] as const;
export type Level = (typeof LEVELS)[number];

export type LogFilters = {
  level?: Level;
  event?: string;
  hide_http?: boolean;
  call_id?: string;
  request_id?: string;
};
