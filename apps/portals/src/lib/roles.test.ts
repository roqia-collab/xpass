import { describe, expect, it } from "vitest";

import { canAccess, formatDuration, initials, spacesFor } from "./roles";

const m = (role: string) => ({ scope_type: "merchant" as const, scope_id: "x", scope_name: "X", role });

describe("spacesFor", () => {
  it("donne l'espace commerçant à un propriétaire", () => {
    expect(spacesFor({ memberships: [m("merchant_owner")] })).toEqual(["partner"]);
  });

  it("n'ouvre aucun espace sans rattachement", () => {
    expect(spacesFor({ memberships: [] })).toEqual([]);
  });

  it("ne confond pas RH et administration", () => {
    const hr = { memberships: [{ ...m("hr_admin"), scope_type: "organization" as const }] };
    expect(canAccess(hr, "company")).toBe(true);
    expect(canAccess(hr, "admin")).toBe(false);
    expect(canAccess(hr, "partner")).toBe(false);
  });

  it("liste tous les espaces d'un compte mixte", () => {
    expect(
      spacesFor({
        memberships: [
          m("merchant_owner"),
          { ...m("hr_admin"), scope_type: "organization" as const },
          { ...m("platform_admin"), scope_type: "platform" as const, scope_id: null },
        ],
      }),
    ).toEqual(["admin", "company", "partner"]);
  });
});

describe("formats", () => {
  it("initiales", () => expect(initials("Atelier Belle venue")).toBe("AB"));
  it("durées", () => {
    expect(formatDuration(30)).toBe("30 min");
    expect(formatDuration(90)).toBe("1 h 30");
    expect(formatDuration(120)).toBe("2 h");
  });
});
