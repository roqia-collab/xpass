// Types alignés sur contracts/openapi.json (sous-ensemble utilisé par les portails).

export type Space = "partner" | "company" | "admin";

export interface Membership {
  scope_type: "platform" | "merchant" | "organization";
  scope_id: string | null;
  scope_name: string;
  role: string;
}

export interface Me {
  id: string;
  email: string;
  display_name: string;
  is_demo: boolean;
  memberships: Membership[];
}

export interface Offer {
  id: string;
  title: string;
  summary: string;
  includes: string | null;
  duration_min: number;
  price_credits: number;
  booking_mode: "resource_slot" | "capacity_session" | "open_access" | "external_ticket";
  participants_max: number;
  capacity: number | null;
  free_cancellation_hours: number;
}

export interface TeamMember {
  name: string;
  role_label: string;
  kind: "staff" | "equipment" | "room";
}

export interface PartnerLocation {
  id: string;
  slug: string;
  name: string;
  kind_label: string;
  category_name: string;
  subcategory_name: string;
  subcategory_slug: string;
  district_label: string;
  merchant_name: string;
  cover_image_key: string | null;
  address_line: string;
  postal_code: string;
  city_name: string;
  access_info: string | null;
  hours_summary: string;
  opening_hours: { weekday: number; opens_at: string; closes_at: string }[];
  offers: Offer[];
  team: TeamMember[];
  status: string;
  /** Validation XPASS du partenaire (dossier). */
  merchant_status?: CommercialStatus | null;
  wheelchair_accessible: boolean;
}

export type CommercialStatus = "draft" | "pending_review" | "documents_missing" | "approved" | "suspended";
export type PspStatus = "not_started" | "pending" | "verified" | "rejected";

export interface AdminMerchant {
  id: string;
  display_name: string;
  legal_name: string;
  city_label: string;
  market_code: string;
  commercial_status: CommercialStatus;
  psp_status: PspStatus;
  location_count: number;
  is_demo: boolean;
  created_at: string;
}

export interface AdminMerchants {
  by_commercial_status: Record<CommercialStatus, number>;
  items: AdminMerchant[];
}

export interface Organization {
  id: string;
  name: string;
  sector_label: string | null;
  city_label: string | null;
  hr_member_count: number;
  is_demo: boolean;
}

export interface PartnerBooking {
  id: string;
  status: "held" | "confirmed" | "redeemed" | "no_show";
  location_id: string;
  offer_title: string;
  resource_id: string | null;
  resource_name: string | null;
  customer_name: string;
  party_size: number;
  total_credits: number;
  /** Prix figé à la réservation ; peak / demand (majoré) ou last_minute (réduit). */
  price_credits_per_person: number;
  price_adjustments: string[];
  starts_at: string;
  ends_at: string;
  local_start: string; // « 2026-11-02T10:00 », heure murale du lieu
  local_end: string;
}

export interface Payout {
  id: string;
  period_start: string;
  period_end: string;
  currency: string;
  gross_minor: number;
  commission_minor: number;
  adjustments_minor: number;
  net_minor: number;
  visits: number;
  status: "pending" | "in_transit" | "paid" | "to_reconcile" | "failed";
  paid_at: string | null;
  confirmed_minor: number | null;
}

export interface Settlements {
  currency: string;
  psp_status: string;
  payouts_enabled: boolean;
  has_payout_account: boolean;
  psp_configured: boolean;
  is_demo: boolean;
  terms: { gross_minor_per_credit: number; commission_bps: number; currency: string; is_demo: boolean } | null;
  to_receive_minor: number;
  open_period: {
    gross_minor: number;
    commission_minor: number;
    adjustments_minor: number;
    net_minor: number;
    visits: number;
    pending_valuation: number;
  };
  payouts: Payout[];
}

export interface PayoutDetail extends Payout {
  lines: { kind: string; occurred_at: string; offer_title: string; location_name: string; credits: number; gross_minor: number; commission_minor: number }[];
  adjustments: { reference: string; label: string; amount_minor: number }[];
}

export type BookingModeEditable = "resource_slot" | "capacity_session" | "open_access";

export interface ManagedVersion {
  id: string;
  version: number;
  title: string;
  summary: string;
  duration_min: number;
  price_credits: number;
  participants_min: number;
  participants_max: number;
  capacity: number | null;
  free_cancellation_hours: number;
}

export interface ManagedLocation {
  id: string;
  name: string;
  district_label: string;
  can_edit: boolean;
  description: string;
  access_info: string | null;
  meeting_point: string | null;
  wheelchair_accessible: boolean;
  review_url: string | null;
  cover_image_key: string | null;
  offers: {
    id: string;
    booking_mode: BookingModeEditable | "external_ticket";
    is_active: boolean;
    image_key: string | null;
    current: ManagedVersion;
    resource_ids: string[];
    versions_count: number;
  }[];
  resources: { id: string; kind: "staff" | "equipment" | "room"; name: string; role_label: string; is_active: boolean }[];
  hours: { weekday: number; opens_at: string; closes_at: string }[];
  exceptions: { id: string; day: string; is_closed: boolean; opens_at: string | null; closes_at: string | null; reason: string | null }[];
}

export interface PartnerBlock {
  id: string;
  resource_id: string;
  resource_name: string;
  reason: string;
  local_start: string;
  local_end: string;
}

export interface CompanyPolicy {
  credits_per_month: number;
  eligible_categories: string[] | null;
  credit_validity_days: number;
  effective_from: string;
}

export interface CompanyReport {
  period: string;
  currency: string | null;
  eligible: number;
  active: number;
  activation_rate: number;
  monthly_budget_minor: number;
  allocated_credits: number;
  allocated_cost_minor: number;
  consumed_credits: number;
  /** Crédits consommés par des annulations tardives ou des absences (total agrégé). */
  penalty_credits: number;
  consumed_cost_minor: number;
  balance_minor: number;
  categories: { slug: string; name: string; masked: boolean; share: number | null; employees: number | null }[];
  privacy_threshold: number;
}

export interface CompanyOverview {
  organization_name: string;
  can_edit: boolean;
  contract: {
    status: string;
    credit_price_minor: number;
    currency: string;
    starts_on: string;
    term_months: number;
    covered_cities: string[];
    commission_bps: number;
    free_cancellation_hours: number;
    is_demo: boolean;
  } | null;
  policy: CompanyPolicy | null;
  next_policy: CompanyPolicy | null;
  categories: { slug: string; name: string }[];
  report: CompanyReport;
}

export interface CompanyEmployee {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  status: "invited" | "active" | "suspended" | "removed";
  invited_at: string;
  joined_at: string | null;
  credits_this_month: number | null;
}

export interface CsvPreview {
  headers: string[];
  mapping: Record<string, string>;
  valid_count: number;
  duplicate_count: number;
  invalid_count: number;
  errors: { line: number; email: string; last_name: string; first_name: string; problem: string; detail: string }[];
}

export interface CompanyInvoice {
  id: string;
  reference: string;
  label: string;
  amount_minor: number;
  currency: string;
  issued_on: string;
  due_on: string;
  status: "pending" | "paid" | "void";
  paid_at: string | null;
  is_demo: boolean;
}

export interface AllocationDay {
  day: string;
  employees: number;
  credits: number;
  cost_minor: number;
}
