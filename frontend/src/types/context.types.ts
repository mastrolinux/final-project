/**
 * Context profile types matching backend schemas.
 * @see backend/src/schemas/context.py
 */

import type { AccountType } from "./auth.types";
import type { IdentityNameInResolved } from "./profile.types";

export type ContextType =
  | "professional"
  | "social"
  | "legal"
  | "healthcare"
  | "family"
  | "custom";

export const CONTEXT_TYPES: ContextType[] = [
  "professional",
  "social",
  "legal",
  "healthcare",
  "family",
  "custom",
];

export interface ContextProfileCreate {
  context_type: ContextType;
  context_name: string;
  display_name_override?: string;
  email_override?: string;
  phone_override?: string;
  bio?: string;
  is_active?: boolean;
}

export interface ContextProfileUpdate {
  context_name?: string;
  display_name_override?: string | null;
  email_override?: string | null;
  phone_override?: string | null;
  bio?: string | null;
  is_active?: boolean;
}

export interface ContextProfileResponse {
  id: string;
  user_id: string;
  context_type: ContextType;
  context_name: string;
  display_name_override: string | null;
  email_override: string | null;
  phone_override: string | null;
  bio: string | null;
  avatar_override_url: string | null;
  avatar_override_thumbnail_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  valid_from: string;
  valid_to: string | null;
}

export interface ResolvedProfileResponse {
  user_id: string;
  account_type: AccountType;
  display_name: string | null;
  email: string;
  phone: string | null;
  preferred_language: string;
  bio: string | null;
  avatar_url: string | null;
  avatar_thumbnail_url: string | null;
  context_type: ContextType | null;
  context_name: string | null;
  identity_names: IdentityNameInResolved[];
}

/**
 * Context type metadata for UI rendering
 */
export const CONTEXT_TYPE_META: Record<
  ContextType,
  { label: string; color: string; icon: string }
> = {
  professional: {
    label: "Professional",
    color: "blue",
    icon: "BriefcaseIcon",
  },
  social: {
    label: "Social",
    color: "purple",
    icon: "UserGroupIcon",
  },
  legal: {
    label: "Legal",
    color: "green",
    icon: "ScaleIcon",
  },
  healthcare: {
    label: "Healthcare",
    color: "red",
    icon: "HeartIcon",
  },
  family: {
    label: "Family",
    color: "amber",
    icon: "HomeIcon",
  },
  custom: {
    label: "Custom",
    color: "gray",
    icon: "AdjustmentsHorizontalIcon",
  },
};
