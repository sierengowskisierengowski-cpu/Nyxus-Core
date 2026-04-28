import "@fontsource/caveat/700.css";

const blobs = [
  { label: "1", color: "#ff00ff", borderRadius: "62% 38% 46% 54%", shadow: "rgba(255,0,255,0.85)" },
  { label: "2", color: "#ff5500", borderRadius: "38% 62% 54% 46%", shadow: "rgba(255,85,0,0.85)" },
  { label: "3", color: "#e6b800", borderRadius: "70% 30% 38% 62%", shadow: "rgba(230,184,0,0.85)" },
  { label: "4", color: "#39ff14", borderRadius: "30% 70% 62% 38%", shadow: "rgba(57,255,20,0.85)" },
  { label: "5", color: "#0088ff", borderRadius: "54% 46% 30% 70%", shadow: "rgba(0,136,255,0.85)" },
  { label: "6", color: "#cc00ff", borderRadius: "46% 54% 70% 30%", shadow: "rgba(204,0,255,0.85)" },
];

export default function WorkspaceButtons() {
  return (
    <div
      style={{
        background: "#08080e",
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 40,
        fontFamily: "'Caveat', cursive",
        padding: "40px 60px",
      }}
    >
      <p style={{ color: "#555", fontSize: 13, letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>
        Waybar · Workspace Buttons
      </p>

      {/* Horizontal bar (bottom bar layout) */}
      <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
        {blobs.map((b, i) => (
          <BlobBtn key={i} {...b} active={i === 0} />
        ))}
      </div>

      {/* Vertical bar layout */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, alignItems: "center" }}>
        {blobs.map((b, i) => (
          <BlobBtn key={i} {...b} active={i === 3} />
        ))}
      </div>

      <p style={{ color: "#333", fontSize: 11, marginTop: 8 }}>
        top row = horizontal bar &nbsp;·&nbsp; bottom column = vertical bar
      </p>
    </div>
  );
}

function BlobBtn({
  label,
  color,
  borderRadius,
  shadow,
  active,
}: {
  label: string;
  color: string;
  borderRadius: string;
  shadow: string;
  active?: boolean;
}) {
  return (
    <div
      style={{
        width: 42,
        height: 42,
        borderRadius,
        border: `2px solid ${active ? color : color + "88"}`,
        backgroundColor: active ? color + "2e" : "transparent",
        boxShadow: active
          ? `0 0 14px ${shadow}, inset 0 0 8px ${shadow.replace("0.85", "0.15")}`
          : "none",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: active ? color : color + "bb",
        fontSize: 18,
        fontWeight: 700,
        fontFamily: "'Caveat', cursive",
        transition: "all 0.2s",
        cursor: "pointer",
      }}
    >
      {label}
    </div>
  );
}
