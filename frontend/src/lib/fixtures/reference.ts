import type { ReferenceData } from "@/lib/api/types";

/**
 * Fixture reference data, shaped exactly like `GET /reference`. Used by
 * component/unit tests and as a documented example of the contract — not
 * wired into the running app (which always talks to the real API).
 */
export const referenceFixture: ReferenceData = {
  departments: [
    { id: 1, name: "Engineering" },
    { id: 2, name: "Sales" },
    { id: 3, name: "Customer Support" },
    { id: 4, name: "People & Talent" },
    { id: 5, name: "Finance" },
  ],
  job_roles: [
    { id: 1, name: "Software Engineer" },
    { id: 2, name: "Product Manager" },
    { id: 3, name: "Account Executive" },
    { id: 4, name: "Support Specialist" },
    { id: 5, name: "Recruiter" },
  ],
  levels: [
    { id: 1, name: "L2", rank: 2 },
    { id: 2, name: "L3", rank: 3 },
    { id: 3, name: "L4", rank: 4 },
    { id: 4, name: "L5", rank: 5 },
  ],
  countries: [
    { id: 1, name: "India", code: "IN", currency: "INR" },
    { id: 2, name: "United States", code: "US", currency: "USD" },
    { id: 3, name: "United Kingdom", code: "GB", currency: "GBP" },
    { id: 4, name: "Germany", code: "DE", currency: "EUR" },
  ],
  genders: ["female", "male", "non_binary", "undisclosed"],
  employment_statuses: ["active", "on_leave", "terminated"],
  change_reasons: [
    "initial",
    "annual_review",
    "promotion",
    "market_adjustment",
    "role_change",
    "correction",
  ],
  base_currency: "USD",
};
