import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", background: "#2f6b3a" }}>
        <svg width="180" height="180" viewBox="0 0 64 64">
          <path d="M12 30 L32 14 L52 30 V52 H12 Z" fill="#f4efe4" />
          <path d="M22 37 l7 7 l13 -14" fill="none" stroke="#2f6b3a" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    ),
    size,
  );
}
