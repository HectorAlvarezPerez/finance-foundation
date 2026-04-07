import type { InsightsSummary as SharedInsightsSummary } from "@finance-foundation/shared";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export type InsightsRecapMonth = {
  monthKey: string;
  label: string;
  month_key?: string;
  month_label?: string;
};

export type InsightsMonthlyRecapFact = {
  label: string;
  value: string;
  tone?: "neutral" | "positive" | "negative" | "accent";
};

export type InsightsMonthlyRecapVisual =
  | {
      kind: "top_category";
      category_name?: string;
      category_color?: string;
      amount?: number | string;
      share?: number;
      series?: Array<{
        label: string;
        value: number;
        color?: string;
      }>;
    }
  | {
      kind: "biggest_moment";
      amount?: number | string;
      date_label?: string;
      description?: string;
      merchant?: string;
      accent_color?: string;
    }
  | {
      kind: "month_comparison";
      current_amount?: number | string;
      previous_amount?: number | string;
      delta?: number | string;
      current_label?: string;
      previous_label?: string;
      current_color?: string;
      previous_color?: string;
    }
  | {
      kind: string;
      [key: string]: unknown;
    };

export type InsightsMonthlyRecapStory = {
  id: string;
  kind: string;
  headline: string;
  subheadline?: string;
  body?: string;
  theme?: string;
  facts?: InsightsMonthlyRecapFact[];
  visual: InsightsMonthlyRecapVisual;
};

export type InsightsMonthlyRecap = {
  month_key: string;
  month_label: string;
  status: string;
  generated_at?: string | null;
  updated_at?: string | null;
  source_fingerprint?: string;
  is_stale?: boolean;
  stories: InsightsMonthlyRecapStory[];
};

export type InsightsSummaryWithRecapMonths = SharedInsightsSummary & {
  available_recap_months?: Array<
    InsightsRecapMonth | { month_key: string; month_label?: string } | string
  >;
};

export type InsightsMonthlyRecapRegenerateRequest = {
  month_key: string;
};

export type {
  Account,
  AccountCreate,
  AccountType,
  AccountUpdate,
  AuthLoginRequest,
  AuthProvidersRead,
  AuthRegisterRequest,
  Budget,
  BudgetBulkCreate,
  BudgetBulkCreateResponse,
  BudgetCreate,
  BudgetUpdate,
  Category,
  CategoryCreate,
  CategoryType,
  CategoryUpdate,
  InsightsAccountBalance,
  InsightsMonthlyBucket,
  InsightsSummary,
  InsightsTopCategory,
  PaginatedResponse,
  Settings,
  SettingsUpdate,
  Transaction,
  TransactionCreate,
  TransactionImportAnalysisResponse,
  TransactionImportColumnMapping,
  TransactionImportCommitRequest,
  TransactionImportCommitResponse,
  TransactionImportDraft,
  TransactionImportPreviewResponse,
  TransactionUpdate,
  User,
} from "@finance-foundation/shared";
