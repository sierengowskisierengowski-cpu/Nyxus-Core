import { useState } from "react";
import { C, BASE, AppDef } from "./shared";

export function MockupBody({ a }: { a: AppDef }) {
  const installPath = a.install ?? a.download;
  const hasInstallAsset = Boolean(installPath);
  const installUrl = hasInstallAsset
    ? `${window.location.origin}${BASE}/${installPath}`
    : "";
  const installCmd = !hasInstallAsset
    ? "echo \"Install artifact unavailable\""
    : installPath!.endsWith(".sh")
    ? `curl -fsSL "${installUrl}" | bash`
    : `curl -fsSL -O "${installUrl}"`;
  const [copied, setCopied] = useState(false);
  const copy = () => {
    if (!hasInstallAsset) return;
    navigator.clipboard.writeText(installCmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "180px 1fr",
      height: "100%",
      minHeight: 320,
      fontFamily: '"JetBrains Mono", monospace',
      color: C.text,
    }}>
      <div style={{
        background: "rgba(6,4,12,0.55)",
        backdropFilter: "blur(14px) saturate(1.6)",
        WebkitBackdropFilter: "blur(14px) saturate(1.6)",
        borderRight: `1px solid ${a.color}33`,
        padding: "1rem 0.6rem",
        display: "flex", flexDirection: "column", gap: 4,
      }}>
        <div style={{ fontSize: "0.55rem", color: `${a.color}aa`, letterSpacing: "0.22em", padding: "0.3rem 0.5rem", marginBottom: 6 }}>
          MODULES
        </div>
        {a.modules?.map((m, i) => (
          <div key={m} style={{
            fontSize: "0.7rem",
            color: i === 0 ? a.color : C.dim,
            background: i === 0 ? `${a.color}1a` : "transparent",
            border: i === 0 ? `1px solid ${a.color}55` : "1px solid transparent",
            borderLeft: i === 0 ? `3px solid ${a.color}` : "3px solid transparent",
            padding: "0.4rem 0.6rem",
            borderRadius: 2,
            textShadow: i === 0 ? `0 0 5px ${a.color}88` : "none",
            fontFamily: "'Caveat', cursive",
          }}>
            ◈ {m}
          </div>
        ))}
        <div style={{ flex: 1 }} />
        <div style={{ fontSize: "0.5rem", color: "#444", letterSpacing: "0.18em", padding: "0.4rem 0.5rem" }}>
          NYX-J5W-2026
        </div>
      </div>

      <div style={{ padding: "1.2rem 1.5rem", display: "flex", flexDirection: "column", gap: "1rem", overflow: "auto" }}>
        <div>
          <div style={{ fontSize: "0.55rem", color: `${a.color}aa`, letterSpacing: "0.22em", marginBottom: 4 }}>
            {a.tagline}
          </div>
          <div style={{
            fontSize: "1.7rem",
            color: a.color,
            fontWeight: 800,
            letterSpacing: "0.04em",
            textShadow: `0 0 14px ${a.color}66`,
            fontFamily: "'Caveat', cursive",
          }}>
            NYXUS {a.name}
          </div>
        </div>

        <p style={{ margin: 0, fontSize: "0.78rem", color: C.dim, lineHeight: 1.7, maxWidth: 720 }}>
          {a.desc}
        </p>

        <div style={{
          flex: 1,
          minHeight: 140,
          border: `2px dashed ${a.color}44`,
          borderRadius: 4,
          padding: "1rem",
          background: `radial-gradient(ellipse at center, ${a.color}08 0%, transparent 70%)`,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: 8,
        }}>
          <div style={{ fontSize: "2.4rem", color: a.color, textShadow: `0 0 24px ${a.color}` }}>{a.glyph}</div>
          <div style={{ fontSize: "0.65rem", color: a.color, letterSpacing: "0.2em", opacity: 0.7 }}>
            GTK4 PYTHON · NATIVE LINUX APP
          </div>
          <div style={{ fontSize: "0.6rem", color: C.dim, letterSpacing: "0.05em", maxWidth: 420, textAlign: "center" }}>
            Runs natively on the NYXUS desktop. Install on your Hyprland system with the curl command below — this preview is a reference of what's shipped.
          </div>
        </div>

        <div style={{
          background: "rgba(0,0,0,0.65)",
          border: `1px solid ${a.color}33`,
          borderRadius: 3,
          padding: "0.65rem 0.85rem",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <code style={{ flex: 1, fontSize: "0.7rem", color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            <span style={{ color: "#444" }}>$</span> {!hasInstallAsset
              ? "install artifact unavailable"
              : a.install?.endsWith(".sh")
              ? <>curl -fsSL "<span style={{ color: a.color }}>$BASE/{a.install}</span>" | bash</>
              : <>curl -fsSL -O "<span style={{ color: a.color }}>$BASE/{a.download}</span>"</>}
          </code>
          <button
            onClick={copy}
            style={{
              background: copied ? `${a.color}33` : "transparent",
              border: `1px solid ${copied ? a.color : "#333"}`,
              color: copied ? a.color : C.dim,
              padding: "3px 10px",
              borderRadius: 2,
              fontSize: "0.6rem",
              cursor: "pointer",
              letterSpacing: "0.05em",
              opacity: hasInstallAsset ? 1 : 0.5,
            }}
            disabled={!hasInstallAsset}
          >
            {copied ? "COPIED" : "COPY"}
          </button>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          {a.download && (
            <a
              href={`${BASE}/${a.download}`} download={a.download}
              style={{
                flex: 1, textAlign: "center", padding: "0.5rem",
                background: `${a.color}14`, border: `1px solid ${a.color}66`,
                color: a.color, textDecoration: "none",
                fontSize: "0.65rem", letterSpacing: "0.15em",
                borderRadius: 2, fontWeight: 700,
                textShadow: `0 0 6px ${a.color}88`,
              }}
            >
              ▼ DOWNLOAD {a.download}
            </a>
          )}
          {a.install && (
            <a
              href={`${BASE}/${a.install}`} download={a.install}
              style={{
                flex: 1, textAlign: "center", padding: "0.5rem",
                background: "transparent", border: `1px solid ${a.color}33`,
                color: `${a.color}cc`, textDecoration: "none",
                fontSize: "0.65rem", letterSpacing: "0.15em",
                borderRadius: 2, fontWeight: 700,
              }}
            >
              ▼ INSTALL.SH
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
