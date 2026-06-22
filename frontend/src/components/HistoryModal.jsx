import { T } from "./constants.js";

export const HistoryModal = ({ rows, onClose }) => (
  <div
    style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.7)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 1000,
      backdropFilter: "blur(4px)",
    }}
  >
    <div
      className="fu"
      style={{
        background: T.bg1,
        border: `1px solid ${T.border2}`,
      width: "92%",
      maxWidth: 800,
      maxHeight: "85vh",
      overflow: "auto",
      padding: 36,
        boxShadow: `0 40px 80px ${T.bg0}CC, 0 0 0 1px ${T.cyan}10`,
        position: "relative",
      }}
    >
      {/* Top accent */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background: `linear-gradient(90deg, ${T.cyan}80, ${T.violet}60, transparent)`,
        }}
      />

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 22,
        }}
      >
        <div
          style={{
            fontFamily: T.mono,
            fontSize: 11,
            color: T.cyan,
            letterSpacing: 2,
          }}
        >
          LAST 7 CFO DECISIONS
        </div>
        <button
          onClick={onClose}
          style={{
            fontFamily: T.mono,
            fontSize: 10,
            color: T.text2,
            background: "none",
            border: `1px solid ${T.border}`,
            padding: "3px 10px",
            cursor: "pointer",
          }}
        >
          ✕ CLOSE
        </button>
      </div>

      {rows.length === 0 ? (
        <div
          style={{
            fontFamily: T.mono,
            fontSize: 10,
            color: T.text2,
            textAlign: "center",
            padding: 32,
          }}
        >
          No decisions recorded yet.
        </div>
      ) : (
        rows.map((row, idx) => (
            <div
                key={idx}
                style={{
                padding: "14px 16px",
                marginBottom: 10,
                background: T.bg0,
                border: `1px solid ${T.border}`,
                borderLeft: `3px solid ${
                    row.decision === "APPROVED" ? T.green : T.red
                }`,
                }}
            >
                <div
                style={{
                    fontSize: 15,
                    color: T.text0,
                    fontWeight: 600,
                    marginBottom: 8,
                }}
                >
                {row.file_name}
                </div>

                <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 6,
                }}
                >
                <div
                    style={{
                    fontFamily: T.mono,
                    fontSize: 9,
                    color: T.text2,
                    }}
                >
                    Batch ID
                    <div
                    style={{
                        color: T.text1,
                        marginTop: 2,
                        fontSize: 10,
                    }}
                    >
                    {row.batch_id}
                    </div>
                </div>

                <div
                    style={{
                    fontFamily: T.mono,
                    fontSize: 9,
                    color: T.text2,
                    }}
                >
                    Decision
                    <div
                    style={{
                        color:
                        row.decision === "APPROVED"
                            ? T.green
                            : T.red,
                        marginTop: 2,
                        fontSize: 11,
                        fontWeight: 700,
                        textShadow: `0 0 8px ${
                        row.decision === "APPROVED"
                            ? T.green
                            : T.red
                        }60`,
                    }}
                    >
                    {row.decision}
                    </div>
                </div>

                <div
                    style={{
                    fontFamily: T.mono,
                    fontSize: 9,
                    color: T.text2,
                    }}
                >
                    CFO
                    <div
                    style={{
                        color: T.text1,
                        marginTop: 2,
                        fontSize: 10,
                    }}
                    >
                    {row.decided_by}
                    </div>
                </div>

                <div
                    style={{
                    fontFamily: T.mono,
                    fontSize: 9,
                    color: T.text2,
                    }}
                >
                    Time
                    <div
                    style={{
                        color: T.text1,
                        marginTop: 2,
                        fontSize: 10,
                    }}
                    >
                    {new Date(
                        new Date(row.decided_at).getTime() +
                        5.5 * 60 * 60 * 1000
                    ).toLocaleString("en-IN")}
                    </div>
                </div>
                </div>

                {/* CFO COMMENT */}
                {row.comment && (
                <div
                    style={{
                    marginTop: 12,
                    padding: "10px 12px",
                    background: T.bg1,
                    border: `1px solid ${T.border}`,
                    borderLeft: `3px solid ${
                        row.decision === "APPROVED"
                        ? T.green
                        : T.red
                    }`,
                    }}
                >
                    <div
                    style={{
                        fontFamily: T.mono,
                        fontSize: 9,
                        color: T.text2,
                        marginBottom: 4,
                        letterSpacing: 1,
                    }}
                    >
                    CFO COMMENT
                    </div>

                    <div
                    style={{
                        color: T.text1,
                        fontSize: 11,
                        lineHeight: 1.5,
                    }}
                    >
                    {row.comment}
                    </div>
                </div>
                )}
            </div>
        ))
      )}
    </div>
  </div>
);