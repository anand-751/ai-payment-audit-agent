import { T, fmt } from "./constants.js";

export const CFOBatchList = ({ batches, onSelect }) => {
  const scoreColor = (s = 100) =>
    s >= 85
      ? T.green
      : s >= 70
      ? T.amber
      : T.red;

  const statusStyle = (s) =>
    ({
      UNDER_REVIEW: { color: T.amber,  bg: T.amberBg,  border: T.amber  },
      APPROVED:     { color: T.green,  bg: T.greenBg,  border: T.green  },
      REJECTED:     { color: T.red,    bg: T.redBg,    border: T.red    },
    }[s] || { color: T.text1, bg: T.bg3, border: T.border });

  return (
    <div style={{ minHeight: "calc(100vh - 60px)", background: T.bg0 }}>
      {/* Top accent */}
      <div
        style={{
          height: 1,
          background: `linear-gradient(90deg, transparent, ${T.violet}80, transparent)`,
        }}
      />

      <div style={{ maxWidth: 1400, margin: "0 auto", padding: "48px 40px" }}>
        {/* Header */}
        <div className="fu" style={{ marginBottom: 40 }}>
          <div
            style={{
              display: "inline-block",
              fontFamily: T.mono,
              fontSize: 9,
              color: T.violet,
              letterSpacing: 3,
              marginBottom: 10,
              padding: "2px 10px",
              border: `1px solid ${T.violet}40`,
              background: T.violetBg,
            }}
          >
            CFO PORTAL
          </div>
          <h1
            style={{
              fontSize: 26,
              fontWeight: 700,
              marginBottom: 8,
              textAlign: "center",
              marginBottom: 12,
              background: `linear-gradient(135deg, ${T.text0} 60%, ${T.violet})`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Payment Batch Queue
          </h1>
          <p style={{ color: T.text1,textAlign: "center", fontSize: 14, lineHeight: 1.7 }}>
            Select a batch to open the full audit pack and take action.
          </p>
        </div>

        {/* Summary counts */}
        <div
          className="fu s1"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            gap: 1,
            marginBottom: 32,
            background: T.border,
          }}
        >
          {[
            ["Pending Review", batches.filter((b) => b.status === "UNDER_REVIEW").length, T.amber],
            ["Approved",       batches.filter((b) => b.status === "APPROVED").length,     T.green],
            ["Rejected",       batches.filter((b) => b.status === "REJECTED").length,     T.red],
          ].map(([l, v, c]) => (
            <div
              key={l}
              style={{ background: T.bg1, padding: "18px 24px", position: "relative", overflow: "hidden" }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 2,
                  background: `linear-gradient(90deg, ${c}80, transparent)`,
                }}
              />
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 24,
                  fontWeight: 700,
                  color: c,
                  marginBottom: 4,
                  textShadow: `0 0 16px ${c}50`,
                }}
              >
                {v}
              </div>
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 9,
                  color: T.text2,
                  letterSpacing: 1,
                }}
              >
                {l}
              </div>
            </div>
          ))}
        </div>

        {batches.length === 0 ? (
          <div
            style={{
              background: T.bg1,
              border: `1px solid ${T.border}`,
              padding: "48px 32px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontFamily: T.mono,
                fontSize: 11,
                color: T.text2,
                marginBottom: 8,
              }}
            >
              NO BATCHES IN QUEUE
            </div>
            <div
              style={{ fontFamily: T.mono, fontSize: 9, color: T.text2 }}
            >
              Switch to AP Manager and upload a CSV to begin the pipeline.
            </div>
          </div>
        ) : (
          <>
            {/* Column headers */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "2fr 1fr 1fr 80px 90px 80px 100px",
                padding: "8px 20px",
                background: T.bg0,
                borderBottom: `1px solid ${T.border}`,
              }}
            >
              {["BATCH / FILE", "UPLOADED", "PAYMENTS", "TOTAL", "RISK", "FLAGS", "STATUS"].map(
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

            {/* Rows */}
            {batches.map((b, i) => {
              const ss = statusStyle(b.status);
              const accentColor =
                b.status === "UNDER_REVIEW"
                  ? T.amber
                  : b.status === "APPROVED"
                  ? T.green
                  : T.red;

              return (
                <div
                  key={b.id}
                  className={`fu hov-row s${Math.min(i + 1, 5)}`}
                  onClick={() => b.status === "UNDER_REVIEW" && onSelect(b)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1fr 1fr 80px 90px 80px 100px",
                    padding: "16px 20px",
                    background: T.bg1,
                    borderBottom: `1px solid ${T.border}`,
                    borderLeft: `3px solid ${accentColor}`,
                    opacity: b.status !== "UNDER_REVIEW" ? 0.6 : 1,
                    cursor: b.status === "UNDER_REVIEW" ? "pointer" : "default",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontFamily: T.mono,
                        fontSize: 11,
                        color: T.text0,
                        marginBottom: 3,
                      }}
                    >
                      {b.file}
                    </div>
                    <div
                      style={{
                        fontFamily: T.mono,
                        fontSize: 9,
                        color: T.text2,
                      }}
                    >
                      {b.id.slice(0, 28)}...
                    </div>
                  </div>

                  <div>
                    <div
                      style={{
                        fontFamily: T.mono,
                        fontSize: 11,
                        color: T.text0,
                        marginBottom: 3,
                      }}
                    >
                      {b.uploadedBy.split(" ")[0]}
                    </div>
                    <div
                      style={{
                        fontFamily: T.mono,
                        fontSize: 9,
                        color: T.text2,
                      }}
                    >
                        {b.uploadedAt ? new Date(b.uploadedAt).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" }) : ""}
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
                    {b.payments}
                  </div>

                  <div
                    style={{
                      fontFamily: T.mono,
                      fontSize: 11,
                      color: T.text0,
                      alignSelf: "center",
                    }}
                  >
                    {fmt(b.total)}
                  </div>

                  <div style={{ alignSelf: "center" }}>
                    <div
                      style={{
                        fontFamily: T.mono,
                        fontSize: 16,
                        fontWeight: 700,
                        color: scoreColor(b.integrityScore ?? 100),
                        textShadow: `0 0 10px ${scoreColor(b.integrityScore ?? 100)}50`,
                      }}
                    >
                      {b.integrityScore ?? 100}
                    </div>
                    <div
                      style={{
                        fontFamily: T.mono,
                        fontSize: 8,
                        color: T.text2,
                      }}
                    >
                      /100
                    </div>
                  </div>

                  <div
                    style={{
                      fontFamily: T.mono,
                      fontSize: 11,
                      alignSelf: "center",
                    }}
                  >
                    <span style={{ color: T.red }}>{b.redFlags}R</span>
                    <span style={{ color: T.text2, margin: "0 3px" }}>·</span>
                    <span style={{ color: T.amber }}>{b.yellowFlags}Y</span>
                  </div>

                  <div style={{ alignSelf: "center" }}>
                    <span
                      style={{
                        fontFamily: T.mono,
                        fontSize: 9,
                        padding: "3px 8px",
                        color: ss.color,
                        background: ss.bg,
                        border: `1px solid ${ss.border}`,
                      }}
                    >
                      {b.status === "UNDER_REVIEW" ? "REVIEW" : b.status}
                    </span>
                    {b.status === "UNDER_REVIEW" && (
                      <div
                        style={{
                          fontFamily: T.mono,
                          fontSize: 8,
                          color: T.text2,
                          marginTop: 4,
                        }}
                      >
                        open →
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>
    </div>
  );
};