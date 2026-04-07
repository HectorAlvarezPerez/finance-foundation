import type { components } from "./generated/api";

export type Account = components["schemas"]["AccountRead"];
export type AccountCreate = components["schemas"]["AccountCreate"];
export type AccountUpdate = components["schemas"]["AccountUpdate"];

export type AuthLoginRequest = components["schemas"]["AuthLoginRequest"];
export type AuthProvidersRead = components["schemas"]["AuthProvidersRead"];
export type AuthRegisterRequest = components["schemas"]["AuthRegisterRequest"];
export type User = components["schemas"]["AuthUserRead"];

export type Budget = components["schemas"]["BudgetRead"];
export type BudgetCreate = components["schemas"]["BudgetCreate"];
export type BudgetBulkCreate = components["schemas"]["BudgetBulkCreate"];
export type BudgetBulkCreateResponse = components["schemas"]["BudgetBulkCreateResponse"];
export type BudgetUpdate = components["schemas"]["BudgetUpdate"];

export type Category = components["schemas"]["CategoryRead"];
export type CategoryCreate = components["schemas"]["CategoryCreate"];
export type CategoryUpdate = components["schemas"]["CategoryUpdate"];

export type Transaction = components["schemas"]["TransactionRead"];
export type TransactionCreate = components["schemas"]["TransactionCreate"];
export type TransactionUpdate = components["schemas"]["TransactionUpdate"];
export type TransactionImportAnalysisResponse =
  components["schemas"]["TransactionImportAnalysisResponse"];
export type TransactionImportColumnMapping =
  components["schemas"]["TransactionImportColumnMapping"];
export type TransactionImportCommitRequest =
  components["schemas"]["TransactionImportCommitRequest"];
export type TransactionImportCommitResponse =
  components["schemas"]["TransactionImportCommitResponse"];
export type TransactionImportDraft = components["schemas"]["TransactionImportDraft"];
export type TransactionImportPreviewResponse =
  components["schemas"]["TransactionImportPreviewResponse"];

export type Settings = components["schemas"]["SettingsRead"];
export type SettingsUpdate = components["schemas"]["SettingsUpdate"];

export type InsightsTopCategory = components["schemas"]["InsightsTopCategoryRead"];
export type InsightsMonthlyBucket = components["schemas"]["InsightsMonthlyBucketRead"];
export type InsightsAccountBalance = components["schemas"]["InsightsAccountBalanceRead"];
export type InsightsMonthlyRecapMonth = components["schemas"]["InsightsMonthlyRecapMonthRead"];
export type InsightsMonthlyRecapFact = components["schemas"]["InsightsMonthlyRecapFactRead"];
export type InsightsMonthlyRecapVisualDatum =
  components["schemas"]["InsightsMonthlyRecapVisualDatumRead"];
export type InsightsMonthlyRecapVisual = components["schemas"]["InsightsMonthlyRecapVisualRead"];
export type InsightsMonthlyRecapStory = components["schemas"]["InsightsMonthlyRecapStoryRead"];
export type InsightsMonthlyRecap = components["schemas"]["InsightsMonthlyRecapRead"];
export type InsightsMonthlyRecapRegenerateRequest =
  components["schemas"]["InsightsMonthlyRecapRegenerateRequest"];
export type InsightsSummary = components["schemas"]["InsightsSummaryRead"];

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type AccountType = components["schemas"]["AccountType"];
export type CategoryType = components["schemas"]["CategoryType"];
