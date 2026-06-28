import { useState } from "react";
import { T, fmt, fmtFull, parseUTCDate } from "./constants.js";

const formatISTDateTime = (date) => {
  try {
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    const parts = formatter.formatToParts(date);
    const p = {};
    parts.forEach((part) => {
      p[part.type] = part.value;
    });
    return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second}`;
  } catch (e) {
    return date.toISOString().slice(0, 19).replace("T", " ");
  }
};

const formatISTDateOnly = (date) => {
  try {
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    const parts = formatter.formatToParts(date);
    const p = {};
    parts.forEach((part) => {
      p[part.type] = part.value;
    });
    return `${p.year}-${p.month}-${p.day}`;
  } catch (e) {
    return date.toISOString().slice(0, 10);
  }
};

export const CFODashboard = ({ batch, apiBase, user, onBack, onDecision }) => {
  const { metadata, violations, cfo_summary } = batch;
  const [filter, setFilter] = useState("ALL");
  const [comment, setComment] = useState("");
  const [decided, setDecided] = useState(null);

  const scoreColor =
    metadata.integrity_score >= 85
      ? T.green
      : metadata.integrity_score >= 60
      ? T.amber
      : T.red;

  const TYPE_LABEL = {
    DUPLICATE_PAYMENT:   "Duplicate",
    MISSING_APPROVAL:    "Unapproved",
    INVALID_VENDOR:      "Invalid Vendor",
    AMOUNT_MISMATCH:     "Amt Mismatch",
    BANK_ROUTING_MISMATCH: "Routing",
    EARLY_PAY_DISCOUNT:  "Discount",
  };

  const filtered =
    filter === "ALL"
      ? violations
      : violations.filter((v) => v.severity === filter);

  const act = (d) => {
    setDecided(d);
    onDecision(batch, d, comment);
  };



  const handleExportLogs = async () => {
    try {
      const response = await fetch(
        `${apiBase}/export-log/${metadata.batch_id}`
      );

      if (!response.ok) {
        throw new Error("Failed to export audit report");
      }

      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");

      link.href = url;

      link.download = `${metadata.batch_id}.pdf`;

      document.body.appendChild(link);

      link.click();

      link.remove();

      window.URL.revokeObjectURL(url);

    } catch (err) {
      console.error(err);
      alert("Failed to export PDF report");
    }
  };

  if (decided)
    return (
      <div
        style={{
          minHeight: "calc(100vh - 60px)",
          background: T.bg0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div className="fu" style={{ textAlign: "center", padding: 48 }}>
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 64,
              marginBottom: 16,
              color: decided === "AUTHORIZE" ? T.green : T.red,
              textShadow: `0 0 30px ${
                decided === "AUTHORIZE" ? T.green : T.red
              }80`,
            }}
          >
            {decided === "AUTHORIZE" ? "✓" : "✕"}
          </div>
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 13,
              color: T.text0,
              marginBottom: 8,
              letterSpacing: 1,
            }}
          >
            {decided === "AUTHORIZE"
              ? "BATCH AUTHORIZED FOR DISBURSEMENT"
              : "BATCH REJECTED — RETURNED TO AP"}
          </div>
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 9,
              color: T.text2,
              marginBottom: 6,
            }}
          >
            {metadata.batch_id}
          </div>
          <div
            style={{ fontFamily: T.mono, fontSize: 9, color: T.text2 }}
          >
            CFO: {user?.name?.toUpperCase()} ·{" "}
            {formatISTDateTime(new Date())} IST
          </div>
        </div>
      </div>
    );

  return (
    <div style={{ minHeight: "calc(100vh - 60px)", background: T.bg0 }}>
      {/* Top accent */}
      <div
        style={{
          height: 1,
          background: `linear-gradient(90deg, transparent, ${T.violet}80, transparent)`,
        }}
      />
      <div
        style={{ maxWidth: 1400, margin: "0 auto", padding: "40px 40px" }}
      >
        {/* Header row */}
        <div
          className="fu"
          style={{
            textAlign: "center",
            marginBottom: 28,
          }}
        >
          <div
            style={{
              display: "inline-block",
              fontFamily: T.mono,
              fontSize: 9,
              color: T.violet,
              letterSpacing: 3,
              marginBottom: 8,
              padding: "2px 10px",
              border: `1px solid ${T.violet}40`,
              background: T.violetBg,
            }}
          >
            PAYMENT RUN AUTHORISATION PACK
          </div>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              marginBottom: 4,
            }}
          >
            {batch.file}
          </h1>
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 10,
              color: T.text2,
              marginBottom: 6,
            }}
          >
            {metadata.batch_id} · Uploaded {batch.uploadedAt ? parseUTCDate(batch.uploadedAt).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" }) : ""} by{" "}
            {batch.uploadedBy}
          </div>
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 9,
              color: T.red,
              letterSpacing: 2,
              animation: "pulse 2s infinite",
              display: "inline-block",
            }}
          >
            ● AWAITING CFO DECISION
          </div>
          <span
            style={{
              fontFamily: T.mono,
              fontSize: 9,
              color: T.text2,
              marginLeft: 12,
            }}
          >
            {metadata.integrity_label}
          </span>
        </div>

        {/* KPI strip */}
        <div
          className="fu s1"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4,1fr)",
            gap: 1,
            marginBottom: 1,
            background: T.border,
          }}
        >
          {[
            {
              l: "TOTAL BATCH VALUE",
              v: fmt(metadata.total_batch_amount),
              s: `${batch.payments} payments`,
              c: T.text0,
            },
            {
              l: "HIGH-RISK EXPOSURE",
              v: fmt(metadata.high_risk_exposure),
              s: `${metadata.total_blocked_payments} blocked`,
              c: T.red,
            },
            {
              l: "INTEGRITY SCORE",
              v: `${metadata.integrity_score}/100`,
              s: metadata.integrity_label,
              c: scoreColor,
            },
            {
              l: "FLAGS",
              v: `${metadata.red_flags}R  ${metadata.yellow_flags}Y`,
              s: "RED · AMBER",
              c: T.amber,
            },
          ].map(({ l, v, s, c }) => (
            <div
              key={l}
              style={{
                background: T.bg1,
                padding: "20px 22px",
                position: "relative",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 2,
                  background: `linear-gradient(90deg, ${c}60, transparent)`,
                }}
              />
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 9,
                  color: T.text2,
                  letterSpacing: 2,
                  marginBottom: 8,
                }}
              >
                {l}
              </div>
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 22,
                  fontWeight: 700,
                  color: c,
                  marginBottom: 4,
                  textShadow: `0 0 12px ${c}40`,
                }}
              >
                {v}
              </div>
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 9,
                  color: T.text2,
                }}
              >
                {s}
              </div>
            </div>
          ))}
        </div>

        {/* Sub-flag strip */}
        <div
          className="fu s2"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(6,1fr)",
            gap: 1,
            marginBottom: 28,
            background: T.border,
          }}
        >
          {[
            ["DUPLICATE",  metadata.duplicate_count,        T.red],
            ["UNAPPROVED", metadata.approval_failures,      T.red],
            ["BAD VENDOR", metadata.vendor_issues,          T.red],
            ["AMT DIFF",   metadata.amount_mismatches,      T.red],
            ["ROUTING",    metadata.routing_issues,         T.amber],
            [
              "DISCOUNTS",
              metadata.discount_opportunities,
              T.amber,
              `avail ${metadata.discount_available_count || 0} / missed ${metadata.discount_missed_count || 0}`,
            ],
          ].map(([l, n, c, s]) => (
            <div
              key={l}
              style={{
                background: T.bg1,
                padding: "12px 14px",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 20,
                  fontWeight: 700,
                  color: n > 0 ? c : T.text2,
                  marginBottom: 2,
                  textShadow: n > 0 ? `0 0 10px ${c}50` : "none",
                }}
              >
                {n}
              </div>
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 8,
                  color: T.text2,
                  letterSpacing: 1,
                }}
              >
                {l}
              </div>
              {s && (
                <div
                  style={{
                    fontFamily: T.mono,
                    fontSize: 7,
                    color: T.text2,
                    marginTop: 2,
                  }}
                >
                  {s}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* AI Narrative */}
        <div
          className="fu s3"
          style={{
            background: T.bg1,
            border: `1px solid ${T.border}`,
            padding: "22px 26px",
            marginBottom: 22,
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: 1,
              background: `linear-gradient(90deg, ${T.cyan}60, ${T.violet}60, transparent)`,
            }}
          />
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: T.cyan,
                boxShadow: `0 0 8px ${T.cyan}`,
                animation: "pulse 2s infinite",
              }}
            />
            <span
              style={{
                fontFamily: T.mono,
                fontSize: 9,
                color: T.cyan,
                letterSpacing: 2,
              }}
            >
              AI CONTROLLER NARRATIVE
            </span>
          </div>
          <div
            style={{
              color: T.text0,
              fontSize: 14,
              lineHeight: 1.9,
              fontWeight: 400,
              letterSpacing: "0.2px",
            }}
          >
            {cfo_summary}
          </div>
        </div>

        {/* Blocked payments */}
        {metadata.blocked_payment_ids?.length > 0 && (
          <div
            className="fu s3"
            style={{
              background: T.redBg,
              border: `1px solid ${T.redDim}`,
              padding: "14px 22px",
              marginBottom: 22,
            }}
          >
            <div
              style={{
                fontFamily: T.mono,
                fontSize: 9,
                color: T.red,
                letterSpacing: 2,
                marginBottom: 10,
              }}
            >
              PAYMENTS ON HOLD — DO NOT DISBURSE
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {metadata.blocked_payment_ids.map((id) => (
                <span
                  key={id}
                  style={{
                    fontFamily: T.mono,
                    fontSize: 11,
                    color: T.red,
                    border: `1px solid ${T.redDim}`,
                    padding: "3px 12px",
                    background: T.bg0,
                  }}
                >
                  {id}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Exception ledger */}
        <div
          className="fu s4"
          style={{
            background: T.bg1,
            border: `1px solid ${T.border}`,
            marginBottom: 22,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "14px 22px",
              borderBottom: `1px solid ${T.border}`,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span
                style={{
                  fontFamily: T.mono,
                  fontSize: 9,
                  color: T.amber,
                  letterSpacing: 2,
                }}
              >
                ⚠ EXCEPTION LEDGER
              </span>
              <span
                style={{
                  fontFamily: T.mono,
                  fontSize: 9,
                  color: T.text2,
                }}
              >
                {violations.length} violations
              </span>
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              {["ALL", "RED", "YELLOW"].map((f) => (
                <button
                  key={f}
                  className="filter-btn"
                  onClick={() => setFilter(f)}
                  style={{
                    fontFamily: T.mono,
                    fontSize: 9,
                    padding: "3px 9px",
                    background: "transparent",
                    border: `1px solid ${filter === f ? T.cyan : T.border}`,
                    color: filter === f ? T.cyan : T.text2,
                    letterSpacing: 1,
                    cursor: "pointer",
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "90px minmax(0, 1fr) 120px 90px 180px",
              padding: "8px 22px",
              background: T.bg0,
              borderBottom: `1px solid ${T.border}`,
            }}
          >
            {["PAY ID", "VENDOR / REASON", "AMOUNT", "SEV", "VIOLATION"].map(
              (h) => (
                <div
                  key={h}
                  style={{
                    fontFamily: T.mono,
                    fontSize: 9,
                    color: T.text2,
                    letterSpacing: 1,
                  }}
                >
                  {h}
                </div>
              )
            )}
          </div>

          {filtered.map((v, i) => {
            const isR = v.severity === "RED";
            const sc = isR ? T.red : T.amber;
            return (
              <div
                key={i}
                className="hov-row"
                style={{
                  display: "grid",
                  gridTemplateColumns: "90px minmax(0, 1fr) 120px 90px 180px",
                  padding: "12px 22px",
                  borderBottom: `1px solid ${T.border}`,
                  background: "transparent",
                  borderLeft: `3px solid ${sc}`,
                  alignItems: "center",
                }}
              >
                <div
                  style={{
                    fontFamily: T.mono,
                    fontSize: 11,
                    color: T.text0,
                    fontWeight: 600,
                    alignSelf: "center",
                  }}
                >
                  {v.payment_id}
                </div>
                <div>
                  <div
                    style={{
                      fontSize: 12,
                      color: T.text0,
                      marginBottom: 2,
                    }}
                  >
                    {v.vendor || "—"}
                  </div>
                  <div
                    style={{
                      fontFamily: T.mono,
                      fontSize: 9,
                      color: T.text2,
                    }}
                  >
                    {v.reason}
                  </div>
                </div>
                <div
                  style={{
                    fontFamily: T.mono,
                    fontSize: 11,
                    color: T.text0,
                    alignSelf: "center",
                  }}
                >
                  {v.amount != null ? fmtFull(v.amount) : (batch.payments && violations[i]?.amount !== undefined ? fmtFull(violations[i].amount) : "N/A")}
                </div>
                <div style={{ alignSelf: "center" }}>
                  <span
                    style={{
                      fontFamily: T.mono,
                      fontSize: 9,
                      color: sc,
                      background: isR ? T.redBg : T.amberBg,
                      padding: "2px 7px",
                      border: `1px solid ${isR ? T.redDim : T.amber}40`,
                    }}
                  >
                    {v.severity}
                  </span>
                </div>
                <div
                  style={{
                    fontFamily: T.mono,
                    fontSize: 10,
                    color: sc,
                    alignSelf: "center",
                    whiteSpace: "normal",
                    overflowWrap: "anywhere",
                    wordBreak: "break-word",
                    lineHeight: 1.25,
                  }}
                >
                  {TYPE_LABEL[v.violation_type] || v.violation_type}
                </div>
              </div>
            );
          })}
        </div>

        {/* CFO Decision Desk */}
        <div
          className="fu s5"
          style={{
            background: T.bg1,
            border: `1px solid ${T.border}`,
            padding: "22px 26px",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: 1,
              background: `linear-gradient(90deg, ${T.violet}80, ${T.cyan}60, transparent)`,
            }}
          />
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 9,
              color: T.violet,
              letterSpacing: 2,
              marginBottom: 18,
            }}
          >
            ⚡ CFO FINAL DISPOSITION DESK
          </div>

          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                fontFamily: T.mono,
                fontSize: 9,
                color: T.text2,
                letterSpacing: 1,
                marginBottom: 8,
              }}
            >
              CONTROLLER NOTES
            </div>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              placeholder="Add justification, conditions, or instructions for AP team..."
              style={{
                width: "100%",
                background: T.bg0,
                border: `1px solid ${T.border}`,
                color: T.text0,
                fontFamily: T.mono,
                fontSize: 12,
                padding: "10px 14px",
                transition: "border-color .2s",
              }}
            />
          </div>

          <div
            style={{
              fontFamily: T.mono,
              fontSize: 9,
              color: T.text2,
              marginBottom: 14,
            }}
          >
            DIGITAL SIGN-OFF · CFO: {user?.name?.toUpperCase()} ·{" "}
            {formatISTDateOnly(new Date())}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: 10,
            }}
          >
            <button
              className="hov-btn"
              onClick={() => act("REJECT")}
              style={{
                padding: "13px 0",
                background: T.redBg,
                border: `1px solid ${T.red}`,
                color: T.red,
                fontFamily: T.mono,
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: 2,
                cursor: "pointer",
              }}
            >
              ✕ REJECT & RETURN
            </button>
            <button
              className="hov-btn"
              onClick={handleExportLogs}
              style={{
                padding: "13px 0",
                background: T.bg0,
                border: `1px solid ${T.border2}`,
                color: T.text1,
                fontFamily: T.mono,
                fontSize: 10,
                letterSpacing: 2,
                cursor: "pointer",
              }}
            >
              ↓ EXPORT AUDIT LOG
            </button>
            <button
              className="hov-btn"
              onClick={() => act("AUTHORIZE")}
              style={{
                padding: "13px 0",
                background: T.greenBg,
                border: `1px solid ${T.green}`,
                color: T.green,
                fontFamily: T.mono,
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: 2,
                cursor: "pointer",
              }}
            >
              ✓ AUTHORIZE DISBURSEMENT
            </button>
          </div>

          <div
            style={{
              marginTop: 10,
              fontFamily: T.mono,
              fontSize: 8,
              color: T.text2,
              textAlign: "center",
            }}
          >
            Action is final and cryptographically logged · Cannot be undone
            without compliance override
          </div>
        </div>
      </div>
    </div>
  );
};