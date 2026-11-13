import { describe, it, expect } from "vitest";
import { computeBBoxPixels } from "@/components/documents/BBoxOverlay";

describe("computeBBoxPixels - Coordinate Scaling & Rotation", () => {
  const sampleBBox: [number, number, number, number] = [0.10, 0.20, 0.50, 0.60];
  const pageWidth = 1000;
  const pageHeight = 800;

  it("calculates exact pixel coordinates at 100% zoom (1.0x) and 0 rotation", () => {
    const rect = computeBBoxPixels(sampleBBox, pageWidth, pageHeight, 1.0, 0);
    expect(rect.left).toBeCloseTo(100);
    expect(rect.top).toBeCloseTo(160);
    expect(rect.width).toBeCloseTo(400);
    expect(rect.height).toBeCloseTo(320);
  });

  it("scales coordinates linearly with zoom factors (1.5x and 2.0x)", () => {
    const rect15 = computeBBoxPixels(sampleBBox, pageWidth, pageHeight, 1.5, 0);
    expect(rect15.left).toBeCloseTo(150);
    expect(rect15.top).toBeCloseTo(240);
    expect(rect15.width).toBeCloseTo(600);
    expect(rect15.height).toBeCloseTo(480);

    const rect20 = computeBBoxPixels(sampleBBox, pageWidth, pageHeight, 2.0, 0);
    expect(rect20.left).toBeCloseTo(200);
    expect(rect20.top).toBeCloseTo(320);
    expect(rect20.width).toBeCloseTo(800);
    expect(rect20.height).toBeCloseTo(640);
  });

  it("correctly transforms coordinates under 90-degree clockwise rotation", () => {
    // Under 90 deg:
    // left = (1.0 - y1) * pageHeight = (1.0 - 0.6) * 800 = 320
    // top = x0 * pageWidth = 0.1 * 1000 = 100
    // width = (y1 - y0) * pageHeight = 0.4 * 800 = 320
    // height = (x1 - x0) * pageWidth = 0.4 * 1000 = 400
    const rect90 = computeBBoxPixels(sampleBBox, pageWidth, pageHeight, 1.0, 90);
    expect(rect90.left).toBeCloseTo(320);
    expect(rect90.top).toBeCloseTo(100);
    expect(rect90.width).toBeCloseTo(320);
    expect(rect90.height).toBeCloseTo(400);
  });

  it("correctly transforms coordinates under 180-degree rotation", () => {
    // Under 180 deg:
    // left = (1.0 - x1) * pageWidth = (1.0 - 0.5) * 1000 = 500
    // top = (1.0 - y1) * pageHeight = (1.0 - 0.6) * 800 = 320
    // width = 400, height = 320
    const rect180 = computeBBoxPixels(sampleBBox, pageWidth, pageHeight, 1.0, 180);
    expect(rect180.left).toBeCloseTo(500);
    expect(rect180.top).toBeCloseTo(320);
    expect(rect180.width).toBeCloseTo(400);
    expect(rect180.height).toBeCloseTo(320);
  });

  it("correctly transforms full page bounding box [0, 0, 1, 1]", () => {
    const fullBBox: [number, number, number, number] = [0, 0, 1, 1];
    const rect = computeBBoxPixels(fullBBox, pageWidth, pageHeight, 1.0, 0);
    expect(rect.left).toBe(0);
    expect(rect.top).toBe(0);
    expect(rect.width).toBe(1000);
    expect(rect.height).toBe(800);
  });
});
