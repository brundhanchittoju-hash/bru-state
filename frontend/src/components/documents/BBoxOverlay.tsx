import React from "react";

export interface PixelRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * Computes pixel coordinates for a normalized bounding box [x0, y0, x1, y1]
 * given canvas dimensions, zoom factor, and page rotation (0, 90, 180, 270 degrees).
 */
export function computeBBoxPixels(
  bbox: [number, number, number, number],
  pageWidth: number,
  pageHeight: number,
  zoom: number = 1.0,
  rotation: number = 0
): PixelRect {
  const [x0, y0, x1, y1] = bbox;
  const normRot = ((rotation % 360) + 360) % 360;

  if (normRot === 90) {
    // 90 deg clockwise: page width and height swap
    const left = (1.0 - y1) * pageHeight * zoom;
    const top = x0 * pageWidth * zoom;
    const width = (y1 - y0) * pageHeight * zoom;
    const height = (x1 - x0) * pageWidth * zoom;
    return { left, top, width, height };
  }

  if (normRot === 180) {
    const left = (1.0 - x1) * pageWidth * zoom;
    const top = (1.0 - y1) * pageHeight * zoom;
    const width = (x1 - x0) * pageWidth * zoom;
    const height = (y1 - y0) * pageHeight * zoom;
    return { left, top, width, height };
  }

  if (normRot === 270) {
    const left = y0 * pageHeight * zoom;
    const top = (1.0 - x1) * pageWidth * zoom;
    const width = (y1 - y0) * pageHeight * zoom;
    const height = (x1 - x0) * pageWidth * zoom;
    return { left, top, width, height };
  }

  // Default: 0 degrees
  const left = x0 * pageWidth * zoom;
  const top = y0 * pageHeight * zoom;
  const width = (x1 - x0) * pageWidth * zoom;
  const height = (y1 - y0) * pageHeight * zoom;

  return { left, top, width, height };
}

interface BBoxOverlayProps {
  bbox: [number, number, number, number];
  pageWidth: number;
  pageHeight: number;
  zoom?: number;
  rotation?: number;
  label?: string;
  isActive?: boolean;
  color?: string;
  onClick?: () => void;
}

export const BBoxOverlay: React.FC<BBoxOverlayProps> = ({
  bbox,
  pageWidth,
  pageHeight,
  zoom = 1.0,
  rotation = 0,
  label,
  isActive = false,
  color = "#4338CA", // cobalt-700
  onClick,
}) => {
  const rect = computeBBoxPixels(bbox, pageWidth, pageHeight, zoom, rotation);

  return (
    <div
      onClick={onClick}
      style={{
        left: `${rect.left}px`,
        top: `${rect.top}px`,
        width: `${rect.width}px`,
        height: `${rect.height}px`,
        borderColor: color,
        backgroundColor: isActive ? `${color}25` : `${color}12`,
      }}
      className={`absolute cursor-pointer border-2 transition-all duration-150 rounded-sm group select-none pointer-events-auto ${
        isActive
          ? "ring-2 ring-primary/50 ring-offset-1 z-30 shadow-md animate-pulse"
          : "hover:border-primary hover:bg-primary/20 z-20"
      }`}
    >
      {label && (
        <span
          style={{ backgroundColor: color }}
          className="absolute -top-5 left-0 px-1.5 py-0.2 rounded text-[10px] font-mono font-medium text-white shadow-sm whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-40"
        >
          {label}
        </span>
      )}
    </div>
  );
};
