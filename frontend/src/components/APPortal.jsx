import { useRef, useState } from "react";
import { T, fmt } from "./constants.js";

export const APPortal = ({ batches, onUpload }) => {
  const [files, setFiles] = useState([]);  const [drag, setDrag] = useState(false);
  const [phase, setPhase] = useState(0);
  const [progress, setProgress] = useState(0);
  const [stepLabel, setStepLabel] = useState("");
  const [error, setError] = useState(null);
  const fileRef = useRef();

  const STEPS = [
    "Ingesting CSV payload...",
    "Validating schema integrity...",
    "Rule 1: Duplicate invoice check...",
    "Rule 2: Approval verification...",
    "Rule 3: Vendor master lookup...",
    "Rule 4: Amount discrepancy check...",
    "Rule 5: Bank routing validation...",
    "Rule 6: Early payment discount scan...",
    "Generating AI controller narrative...",
    "Compiling audit package...",
  ];

  const pickFiles = (selectedFiles) => {
    const csvFiles = Array.from(selectedFiles).filter(
      (f) => f.name.endsWith(".csv")
    );

    setFiles(csvFiles);
  };

  const submit = () => {
    if (!files.length || phase) return;
    setPhase(1);
    setProgress(0);
    let i = 0;
    const iv = setInterval(() => {
      i++;
      setProgress(Math.min(i * 10, 95));
      setStepLabel(STEPS[Math.min(i - 1, STEPS.length - 1)]);
      if (i >= STEPS.length) {
        clearInterval(iv);
        setTimeout(async () => {
          setProgress(100);
          setStepLabel("Audit complete — batch routed to CFO.");
          setError(null);
          try {
            await onUpload(files);
            setPhase(2);
          } catch (err) {
            setPhase(0);
            setError(err?.message || "Upload failed. Please try again.");
            setStepLabel("Upload failed — please retry.");
          }
        }, 500);
      }
    }, 300);
  };

  const reset = () => {
    setFiles([]);
    setPhase(0);
    setProgress(0);
    setStepLabel("");
    setError(null);
  };

  const statusColor = (s) =>
    s === "APPROVED" ? T.green : s === "REJECTED" ? T.red : T.amber;
  const statusBg = (s) =>
    s === "APPROVED" ? T.greenBg : s === "REJECTED" ? T.redBg : T.amberBg;

  // ── Done state ──────────────────────────────────────────────────────────────
  if (phase === 2)
    return (
      <div style={{ minHeight: "calc(100vh - 60px)", background: T.bg0 }}>
        <div
          style={{
            maxWidth: 720,
            margin: "0 auto",
            padding: "80px 40px",
            textAlign: "center",
          }}
        >
          <div
            className="fu"
            style={{
              background: T.bg1,
              border: `1px solid ${T.border}`,
              padding: "48px 40px",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {/* Glow stripe */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: 2,
                background: `linear-gradient(90deg, transparent, ${T.green}, transparent)`,
              }}
            />
            <div
              style={{
                fontSize: 48,
                marginBottom: 20,
                color: T.green,
                textShadow: `0 0 20px ${T.green}80`,
              }}
            >
              ✓
            </div>
            <div
              style={{
                fontFamily: T.mono,
                fontSize: 13,
                color: T.green,
                letterSpacing: 2,
                marginBottom: 10,
              }}
            >
              BATCH SUBMITTED SUCCESSFULLY
            </div>
            <div
              style={{
                fontFamily: T.mono,
                fontSize: 10,
                color: T.text2,
                marginBottom: 4,
              }}
            >
              {files.length} file(s) uploaded
            </div>
            <div
              style={{
                fontFamily: T.mono,
                fontSize: 10,
                color: T.text2,
                marginBottom: 32,
              }}
            >
              Compliance engine complete · CFO notified · Awaiting review
            </div>
            <button
              className="hov-btn"
              onClick={reset}
              style={{
                fontFamily: T.mono,
                fontSize: 11,
                letterSpacing: 2,
                padding: "10px 28px",
                background: "transparent",
                border: `1px solid ${T.border2}`,
                color: T.text1,
              }}
            >
              UPLOAD ANOTHER BATCH
            </button>
          </div>

          {batches.length > 0 && (
            <div
              className="fu s2"
              style={{
                marginTop: 24,
                background: T.bg1,
                border: `1px solid ${T.border}`,
                padding: "20px 24px",
                textAlign: "left",
              }}
            >
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 9,
                  color: T.text2,
                  letterSpacing: 2,
                  marginBottom: 14,
                }}
              >
                RECENT SUBMISSIONS
              </div>
              {batches.slice(0, 3).map((b) => (
                <div
                  key={b.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 0",
                    borderBottom: `1px solid ${T.border}`,
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontFamily: T.mono,
                        fontSize: 11,
                        color: T.text0,
                        marginBottom: 2,
                      }}
                    >
                      {b.file}
                    </div>
                    <div
                      style={{ fontFamily: T.mono, fontSize: 9, color: T.text2 }}
                    >
                      {b.uploadedAt ? new Date(b.uploadedAt).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" }) : ""}
                    </div>
                  </div>
                  <span
                    style={{
                      fontFamily: T.mono,
                      fontSize: 9,
                      padding: "2px 8px",
                      color: statusColor(b.status),
                      border: `1px solid ${statusColor(b.status)}`,
                      background: statusBg(b.status),
                    }}
                  >
                    {b.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );

  // ── Upload / processing state ───────────────────────────────────────────────
  return (
    <div style={{ minHeight: "calc(100vh - 60px)", background: T.bg0 }}>
      {/* Top accent line */}
      <div
        style={{
          height: 1,
          background: `linear-gradient(90deg, transparent, ${T.cyan}60, transparent)`,
        }}
      />
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "48px 40px" }}>
        {/* Header */}
        <div className="fu" style={{ marginBottom: 40 }}>
          <div
            style={{
              display: "inline-block",
              fontFamily: T.mono,
              fontSize: 9,
              color: T.cyan,
              letterSpacing: 3,
              marginBottom: 10,
              padding: "2px 10px",
              border: `1px solid ${T.cyan}40`,
              background: T.cyanBg,
            }}
          >
            AP MANAGER PORTAL
          </div>
          <h1
            style={{
              fontSize: 26,
              fontWeight: 700,
              marginBottom: 8,
              background: `linear-gradient(135deg, ${T.text0} 60%, ${T.cyan})`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Payment Batch Submission
          </h1>
          <p style={{ color: T.text1, fontSize: 14, lineHeight: 1.7 }}>
            Upload your payment batch CSV. The compliance engine validates all
            payments against 6 institutional rules before routing to the CFO.
          </p>
        </div>

        {/* Stats bar */}
        <div
          className="fu s1"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            gap: 1,
            marginBottom: 28,
            background: T.border,
          }}
        >
          {[
            ["6", "Audit Rules"],
            ["90 days", "History Window"],
            ["< 5 min", "To CFO Review"],
          ].map(([v, l]) => (
            <div
              key={l}
              style={{ background: T.bg1, padding: "16px 20px", position: "relative", overflow: "hidden" }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 1,
                  background: `linear-gradient(90deg, ${T.cyan}60, transparent)`,
                }}
              />
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 20,
                  fontWeight: 600,
                  color: T.cyan,
                  marginBottom: 2,
                  textShadow: `0 0 12px ${T.cyan}40`,
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

        {/* Drop zone */}
        <div
          className="fu s2"
          onClick={() => !phase && fileRef.current.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            pickFiles(e.dataTransfer.files);
          }}
          style={{
            border: `1px dashed ${drag ? T.cyan : T.border2}`,
            background: drag ? `${T.cyan}08` : T.bg1,
            padding: "44px 32px",
            textAlign: "center",
            marginBottom: 20,
            cursor: phase ? "default" : "pointer",
            transition: "all .2s",
            boxShadow: drag ? `inset 0 0 30px ${T.cyan}10` : "none",
          }}
        >
          <input
            ref={fileRef}
            type="file"
            multiple
            accept=".csv"
            style={{ display: "none" }}
            onChange={(e) => pickFiles(e.target.files)}
          />
          <div style={{ fontSize: 28, opacity: 0.4, marginBottom: 14 }}>↑</div>
          {files.length > 0 ? (
            <>
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 12,
                  color: T.green,
                  marginBottom: 4,
                }}
              >
                ✓ {files.length} file(s) selected
              </div>
              <div
                style={{ fontFamily: T.mono, fontSize: 9, color: T.text2 }}
              >
                {files.map((f) => (
                  <div key={f.name}>
                    {f.name}
                  </div>
                ))} · Click to replace
              </div>
            </>
          ) : (
            <>
              <div
                style={{ fontSize: 14, color: T.text1, marginBottom: 4 }}
              >
                Drop your .csv file here
              </div>
              <div
                style={{
                  fontFamily: T.mono,
                  fontSize: 9,
                  color: T.text2,
                  letterSpacing: 1,
                }}
              >
                CSV FORMAT REQUIRED
              </div>
            </>
          )}
        </div>

        {/* Required columns */}
        <div
          className="fu s3"
          style={{
            background: T.bg1,
            border: `1px solid ${T.border}`,
            padding: "14px 18px",
            marginBottom: 20,
          }}
        >
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 9,
              color: T.text2,
              letterSpacing: 2,
              marginBottom: 10,
            }}
          >
            REQUIRED COLUMNS
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {[
              "payment_id",
              "vendor_id",
              "vendor_name",
              "invoice_number",
              "amount",
              "bank_routing",
              "authorizer",
              "due_date",
              "invoice_date",
              "early_pay_discount",
              "early_pay_deadline",
            ].map((c) => (
              <span
                key={c}
                style={{
                  fontFamily: T.mono,
                  fontSize: 9,
                  color: T.blue,
                  background: T.bg3,
                  padding: "2px 7px",
                  border: `1px solid ${T.border}`,
                }}
              >
                {c}
              </span>
            ))}
          </div>
        </div>

        {/* Progress bar */}
        {phase === 1 && (
          <div
            className="fu"
            style={{
              background: T.bg1,
              border: `1px solid ${T.border}`,
              padding: "20px",
              marginBottom: 20,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 10,
              }}
            >
              <span
                style={{
                  fontFamily: T.mono,
                  fontSize: 10,
                  color: T.cyan,
                  letterSpacing: 1,
                }}
              >
                PROCESSING
              </span>
              <span
                style={{
                  fontFamily: T.mono,
                  fontSize: 10,
                  color: T.text1,
                }}
              >
                {progress}%
              </span>
            </div>
            <div
              style={{ height: 3, background: T.bg3, marginBottom: 10, borderRadius: 2 }}
            >
              <div
                style={{
                  height: "100%",
                  background: `linear-gradient(90deg, ${T.cyan}, ${T.violet})`,
                  width: `${progress}%`,
                  transition: "width .28s",
                  borderRadius: 2,
                  boxShadow: `0 0 8px ${T.cyan}60`,
                }}
              />
            </div>
            <div
              style={{
                fontFamily: T.mono,
                fontSize: 9,
                color: T.text2,
                animation: "pulse 1.5s infinite",
              }}
            >
              {stepLabel}
            </div>
          </div>
        )}

        {error && (
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 10,
              color: T.red,
              marginBottom: 12,
              textAlign: "center",
            }}
          >
            {error}
          </div>
        )}

        <button
          className="fu s4 hov-btn"
          onClick={submit}
          disabled={!files.length || !!phase}
          style={{
            width: "100%",
            padding: "13px 0",
            background:
              !files.length || phase
                ? T.bg3
                : `linear-gradient(135deg, ${T.cyan}, ${T.violet})`,
            border: "none",
            color:
              !files.length || phase
                ? T.text2
                : T.bg0,
            fontFamily: T.mono,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 2,
            cursor:
              !files.length || phase
                ? "not-allowed"
                : "pointer",
            transition: "all .2s",
          }}
        >
          {phase === 1 ? "RUNNING COMPLIANCE ENGINE..." : "SUBMIT FOR VALIDATION →"}
        </button>
      </div>
    </div>
  );
};