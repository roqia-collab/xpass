/** Types de l'API d'administration (lot 7). */
import type { CommercialStatus, PspStatus } from "./types";

export interface AuditEntry {
  created_at: string;
  actor_kind: "operator" | "system" | "partner" | "customer" | "hr";
  actor_name: string | null;
  action: string;
  object_type: string;
  object_id: string;
  object_label: string;
  reason: string | null;
  details: Record<string, unknown>;
}

export interface QueueItem {
  id: string;
  title: string;
  subtitle: string;
  status: string;
  at: string;
  image_key: string | null;
}

export interface AdminOverview {
  merchants_to_review: number;
  open_disputes: number;
  reconciliation_issues: number;
  merchants: QueueItem[];
  disputes: QueueItem[];
  payouts: Record<string, number>;
  audit: AuditEntry[];
  is_admin: boolean;
  demo_locations: Record<string, number>;
}

export interface ChangeRequestRow {
  id: string;
  location_id: string;
  location_name: string;
  merchant_name: string;
  requested_by: string;
  changes: {
    name?: string;
    kind_label?: string;
    subcategory?: { name: string };
    address?: { label: string; score: number; previous: string };
  };
  status: string;
  decision_reason: string | null;
  created_at: string;
}

export interface MerchantDetail {
  id: string;
  siret: string | null;
  contact_phone: string | null;
  display_name: string;
  legal_name: string;
  city_label: string;
  market_code: string;
  commercial_status: CommercialStatus;
  psp_status: PspStatus;
  psp_account: boolean;
  is_demo: boolean;
  created_at: string;
  checks: { label: string; detail: string; ok: boolean }[];
  locations: {
    id: string;
    name: string;
    slug: string;
    status: string;
    address: string;
    kind_label: string;
    cover_image_key: string | null;
    review_url: string | null;
    published_offers: number;
  }[];
  sandbox: boolean;
  audit: AuditEntry[];
}

export interface ModerationRow {
  id: string;
  name: string;
  merchant_name: string;
  commercial_status: CommercialStatus;
  status: string;
  published_offers: number;
  updated_at: string;
}

export interface DisputeRow {
  id: string;
  reference: string;
  status: string;
  location_name: string;
  customer_name: string;
  created_at: string;
  reason: string;
}

export interface DisputeDetail {
  id: string;
  reference: string;
  status: string;
  reason: string;
  operator_notes: string | null;
  created_at: string;
  updated_at: string;
  resolution_reason: string | null;
  credits_restored: number | null;
  partner_adjustment_minor: number | null;
  customer_name: string;
  location_name: string;
  location_kind: string;
  location_address: string;
  cover_image_key: string | null;
  merchant_id: string;
  offer_title: string;
  booking_status: string;
  local_start: string;
  party_size: number;
  total_credits: number;
  funding: Record<string, number>;
  payable_gross_minor: number | null;
  payable_net_minor: number | null;
  currency: string | null;
  payout_status: string | null;
  payout_paid_at: string | null;
  timeline: AuditEntry[];
  redeemed_at: string | null;
}

export interface Reconciliation {
  payouts: { id: string; merchant_name: string; period_start: string; status: string; net_minor: number; confirmed_minor: number | null; currency: string }[];
  events: { id: string; event_type: string; event_id: string; received_at: string; attempts: number; last_error: string | null; blocked: boolean }[];
  employer_invoices: { id: string; reference: string; organization_name: string; amount_minor: number; currency: string; issued_on: string; due_on: string; is_demo: boolean }[];
  is_admin: boolean;
}

export const DISPUTE_LABEL: Record<string, { label: string; tone: "lavender" | "coral" | "mint" | "grey" }> = {
  open: { label: "Ouvert", tone: "coral" },
  in_review: { label: "En analyse", tone: "lavender" },
  waiting_customer: { label: "Informations demandées", tone: "lavender" },
  resolved_refund: { label: "Restitué", tone: "mint" },
  resolved_rejected: { label: "Rejeté", tone: "grey" },
};

export const ACTOR_LABEL: Record<AuditEntry["actor_kind"], string> = {
  operator: "Opérateur",
  system: "Système",
  partner: "Partenaire",
  customer: "Client",
  hr: "RH",
};

export interface AccessRow {
  id: string;
  email: string;
  display_name: string;
  role: "merchant_owner" | "merchant_staff" | "hr_admin" | "hr_viewer";
  linked: boolean;
  created_at: string;
}

export interface OrgVenue {
  id: string;
  name: string;
  slug: string;
  status: string;
}

export interface OrgMerchant {
  id: string;
  display_name: string;
  city_label: string;
  commercial_status: string;
  owner_email: string | null;
  venues: OrgVenue[];
}

export interface OrganizationRow {
  id: string;
  name: string;
  city_label: string | null;
  is_demo: boolean;
  hr_accounts: number;
  merchants: OrgMerchant[];
}
