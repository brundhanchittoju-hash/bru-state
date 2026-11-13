import { describe, it, expect } from "vitest";
import { getConfidenceDetails } from "@/components/documents/ConfidenceBadge";

describe("getConfidenceDetails - Audit Confidence Tier Logic", () => {
  it("classifies >= 90% as high confidence with green badge", () => {
    const res95 = getConfidenceDetails(0.95);
    expect(res95.level).toBe("high");
    expect(res95.label).toBe("95% High Confidence");
    expect(res95.badgeClass).toContain("emerald");

    const res90 = getConfidenceDetails(0.90);
    expect(res90.level).toBe("high");
    expect(res90.label).toBe("90% High Confidence");
  });

  it("classifies 70% to 89% as medium confidence with blue badge", () => {
    const res85 = getConfidenceDetails(0.85);
    expect(res85.level).toBe("medium");
    expect(res85.label).toBe("85% Confidence");
    expect(res85.badgeClass).toContain("sky");

    const res70 = getConfidenceDetails(0.70);
    expect(res70.level).toBe("medium");
    expect(res70.label).toBe("70% Confidence");
  });

  it("classifies < 70% as low confidence with amber 'Verify manually' warning", () => {
    const res65 = getConfidenceDetails(0.65);
    expect(res65.level).toBe("low");
    expect(res65.label).toBe("65% Verify manually");
    expect(res65.badgeClass).toContain("amber");

    const res40 = getConfidenceDetails(0.40);
    expect(res40.level).toBe("low");
    expect(res40.label).toBe("40% Verify manually");
  });
});
