// import { useState, useEffect } from "react";

// // ── Utils & constants ──────────────────────────────────────────────────────────
// import { getSession, logout } from "./utils/auth";

// // ── Components ─────────────────────────────────────────────────────────────────
// import { GlobalStyles }  from "./components/GlobalStyles";
// import { TopBar }        from "./components/TopBar";
// import { Login }         from "./components/Login";
// import { APPortal }      from "./components/APPortal";
// import { CFOBatchList }  from "./components/CFOBatchList";
// import { CFODashboard }  from "./components/CFODashboard";
// import { HistoryModal }  from "./components/HistoryModal";

// const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// // ── ROOT ───────────────────────────────────────────────────────────────────────
// export default function App() {
//   // ── Auth state ───────────────────────────────────────────────────────────────
//   const [user, setUser] = useState(() => getSession()); // hydrate from sessionStorage

//   // ── Shared app state (preserved across role switch) ──────────────────────────
//   const [batches,       setBatches]       = useState([]);
//   const [selectedBatch, setSelectedBatch] = useState(null);
//   const [notifications, setNotifications] = useState([]);
//   const [showNotifications, setShowNotifications] = useState(false);
//   const [historyRows,   setHistoryRows]   = useState([]);
//   const [showHistory,   setShowHistory]   = useState(false);

//   // Sync sessionStorage → state on mount (handles refresh)
//   useEffect(() => {
//     const session = getSession();
//     if (session) setUser(session);
//   }, []);

//   // ── Handlers ─────────────────────────────────────────────────────────────────
//   const handleLogin = (userPayload) => {
//     setUser(userPayload);
//   };

//   const handleLogout = () => {
//     logout();
//     setUser(null);
//     setSelectedBatch(null);
//   };

//   // const handleSwitch = () => {
//   //   const newUser = switchRole(user.role);
//   //   if (newUser) {
//   //     setUser(newUser);
//   //     setSelectedBatch(null);
//   //   }
//   // };

//   const handleUpload = async (file) => {
//     const formData = new FormData();
//     formData.append("file", file);

//     const uploadRes = await fetch(`${API_BASE}/upload-payment-batch`, {
//       method: "POST",
//       body: formData,
//     });

//     const uploadData = await uploadRes.json();
//     if (!uploadRes.ok) {
//       throw new Error(uploadData.detail || uploadData.message || "Failed to upload batch.");
//     }

//     const batchId = uploadData.data.batch_id;

//     const auditRes = await fetch(`${API_BASE}/run-audit/${batchId}`, {
//       method: "POST",
//     });

//     const auditData = await auditRes.json();
//     if (!auditRes.ok) {
//       throw new Error(auditData.detail || auditData.message || "Failed to run audit.");
//     }

//     const result = auditData.data;

//     const newBatch = {
//       id:               batchId,
//       file:             file.name,
//       uploadedBy:       user.name,
//       uploadedAt:       new Date().toISOString().slice(0, 16).replace("T", " "),
//       status:           result.metadata.decision || "UNDER_REVIEW",
//       payments:         uploadData.data.total_items,
//       total:            uploadData.data.total_amount,
//       riskScore:        result.metadata.risk_score        ?? 0,
//       redFlags:         result.metadata.red_flags         ?? 0,
//       yellowFlags:      result.metadata.yellow_flags      ?? 0,
//       highRiskExposure: result.metadata.high_risk_exposure ?? 0,
//       blockedCount:     result.metadata.total_blocked_payments ?? 0,
//       metadata:         result.metadata,
//       violations:       result.violations  || [],
//       cfo_summary:      result.cfo_summary || "Audit completed. Review the findings in the CFO dashboard.",
//     };

//     setBatches((prev) => [newBatch, ...prev]);
//   };

//   const handleDecision = async (batch, decision, comment) => {
//     const finalDecision = decision === "AUTHORIZE" ? "APPROVED" : "REJECTED";

//     await fetch(`${API_BASE}/batch-decision`, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({
//         batch_id: batch.id,
//         file_name: batch.file,
//         decision: finalDecision,
//         comment,
//       }),
//     });

//     if (decision === "AUTHORIZE") {
//       const emailRes = await fetch(`${API_BASE}/authorize-disbursement`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ batch_id: batch.id, comment }),
//       });

//       if (!emailRes.ok) {
//         const err = await emailRes.json();
//         throw new Error(err.detail || "Failed to send authorization email.");
//       }
//     }

//     setBatches((prev) =>
//       prev.map((b) =>
//         b.id === batch.id ? { ...b, status: finalDecision } : b
//       )
//     );

//     if (decision === "REJECT") {
//       setNotifications((prev) => [
//         {
//           id: Date.now(),
//           batchNo: batch.id,
//           file: batch.file,
//           decision: "REJECTED",
//           message: `Batch ${batch.id} was rejected by CFO`,
//           is_read: false,
//           createdAt: new Date().toISOString(),
//         },
//         ...prev,
//       ]);
//     }

//     setTimeout(() => setSelectedBatch(null), 2200);
//   };

//   const loadHistory = async () => {
//     const res = await fetch(`${API_BASE}/decision-history`);
//     const data = await res.json();
//     setHistoryRows(data.data || []);
//     setShowHistory(true);
//   };

//   const handleOpenNotifications = () => {
//     setShowNotifications((prev) => !prev);
//     setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
//   };

//   // ── Render ────────────────────────────────────────────────────────────────────
//   if (!user) {
//     return (
//       <>
//         <GlobalStyles />
//         <Login onLogin={handleLogin} />
//       </>
//     );
//   }

//   return (
//     <>
//       <GlobalStyles />

//       <TopBar
//         user={user}
//         onLogout={handleLogout}
//         showBack={user.role === "cfo" && !!selectedBatch}
//         onBack={() => setSelectedBatch(null)}
//         notifications={notifications}
//         showNotifications={showNotifications}
//         onOpenNotifications={handleOpenNotifications}
//         onViewHistory={loadHistory}
//       />

//       {/* AP Portal */}
//       {user.role === "ap" && (
//         <APPortal batches={batches} onUpload={handleUpload} />
//       )}

//       {/* CFO Batch List */}
//       {user.role === "cfo" && !selectedBatch && (
//         <CFOBatchList batches={batches} onSelect={setSelectedBatch} />
//       )}

//       {/* CFO Audit Dashboard */}
//       {user.role === "cfo" && selectedBatch && (
//         <CFODashboard
//           batch={selectedBatch}
//           user={user}
//           onBack={() => setSelectedBatch(null)}
//           onDecision={handleDecision}
//         />
//       )}

//       {/* History Modal */}
//       {showHistory && (
//         <HistoryModal rows={historyRows} onClose={() => setShowHistory(false)} />
//       )}
//     </>
//   );
// }




import { useState, useEffect } from "react";

// ── Utils & constants ──────────────────────────────────────────────────────────
import { getSession, logout } from "./components/auth";

// ── Components ─────────────────────────────────────────────────────────────────
import { GlobalStyles } from "./components/GlobalStyles";
import { TopBar } from "./components/TopBar";
import { Login } from "./components/Login";
import { APPortal } from "./components/APPortal";
import { CFOBatchList } from "./components/CFOBatchList";
import { CFODashboard } from "./components/CFODashboard";
import { HistoryModal } from "./components/HistoryModal";

const API_BASE = "/api";

export default function App() {
  const [user, setUser] = useState(() => getSession());

  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [historyRows, setHistoryRows] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    const session = getSession();
    if (session) setUser(session);
  }, []);

  const handleLogin = (userPayload) => {
    setUser(userPayload);
  };

  const handleLogout = () => {
    logout();
    setUser(null);
    setSelectedBatch(null);
  };

  const handleUpload = async (files) => {

    const formData = new FormData();

    files.forEach((file) => {
      formData.append("files", file);
    });

    const uploadRes = await fetch(
      `${API_BASE}/upload-payment-batch`,
      {
        method: "POST",
        body: formData,
      }
    );

    const uploadData = await uploadRes.json();

    if (!uploadRes.ok) {
      throw new Error(
        uploadData.detail ||
        uploadData.message ||
        "Failed to upload batch."
      );
    }

    const uploadedBatches = uploadData.data;

    const createdBatches = [];

    for (const uploaded of uploadedBatches) {

      const batchId = uploaded.batch_id;

      const auditRes = await fetch(
        `${API_BASE}/run-audit/${batchId}`,
        {
          method: "POST",
        }
      );

      const auditData = await auditRes.json();

      if (!auditRes.ok) {
        throw new Error(
          auditData.detail ||
          auditData.message ||
          "Failed to run audit."
        );
      }

      const result = auditData.data;

      createdBatches.push({
        id: batchId,
        file: uploaded.file_name,
        uploadedBy: user.name,
        uploadedAt: new Date().toISOString(),
        status: result.metadata.decision || "UNDER_REVIEW",
        payments: uploaded.batch_info.total_items,
        total: uploaded.batch_info.total_amount,
        integrityScore: result.metadata.integrity_score ?? 0,
        redFlags: result.metadata.red_flags ?? 0,
        yellowFlags: result.metadata.yellow_flags ?? 0,
        highRiskExposure:
          result.metadata.high_risk_exposure ?? 0,
        blockedCount:
          result.metadata.total_blocked_payments ?? 0,
        metadata: result.metadata,
        violations: result.violations || [],
        cfo_summary:
          result.cfo_summary ||
          "Audit completed.",
      });
    }

    setBatches((prev) => [
      ...createdBatches,
      ...prev,
    ]);
  };

  const handleDecision = async (batch, decision, comment) => {
    const finalDecision = decision === "AUTHORIZE" ? "APPROVED" : "REJECTED";

    await fetch(`${API_BASE}/batch-decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        batch_id: batch.id,
        file_name: batch.file,
        decision: finalDecision,
        comment,
      }),
    });

    if (decision === "AUTHORIZE") {
      const emailRes = await fetch(`${API_BASE}/authorize-disbursement`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch_id: batch.id, comment }),
      });

      if (!emailRes.ok) {
        const err = await emailRes.json();
        throw new Error(err.detail || "Failed to send authorization email.");
      }
    }

    setBatches((prev) =>
      prev.map((b) => (b.id === batch.id ? { ...b, status: finalDecision } : b))
    );

    if (decision === "REJECT") {
      setNotifications((prev) => [
        {
          id: Date.now(),
          batchNo: batch.id,
          file: batch.file,
          decision: "REJECTED",
          message: "Rejected by CFO",
          is_read: false,
          createdAt: new Date().toISOString(),
        },
        ...prev,
      ]);
    }

    setTimeout(() => setSelectedBatch(null), 2200);
  };

  const loadHistory = async () => {
    const res = await fetch(`${API_BASE}/decision-history`);
    const data = await res.json();
    setHistoryRows(data.data || []);
    setShowHistory(true);
  };

  const handleOpenNotifications = () => {
    setShowNotifications((prev) => !prev);
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  };

  if (!user) {
    return (
      <>
        <GlobalStyles />
        <Login onLogin={handleLogin} />
      </>
    );
  }

  return (
    <>
      <GlobalStyles />

      <TopBar
        user={user}
        onLogout={handleLogout}
        showBack={user.role === "cfo" && !!selectedBatch}
        onBack={() => setSelectedBatch(null)}
        notifications={notifications}
        showNotifications={showNotifications}
        onOpenNotifications={handleOpenNotifications}
        onViewHistory={loadHistory}
      />

      {user.role === "ap" && (
        <APPortal batches={batches} onUpload={handleUpload} />
      )}

      {user.role === "cfo" && !selectedBatch && (
        <CFOBatchList batches={batches} onSelect={setSelectedBatch} />
      )}

      {user.role === "cfo" && selectedBatch && (
        <CFODashboard
          batch={selectedBatch}
          user={user}
          apiBase={API_BASE}
          onBack={() => setSelectedBatch(null)}
          onDecision={handleDecision}
        />
      )}

      {showHistory && (
        <HistoryModal rows={historyRows} onClose={() => setShowHistory(false)} />
      )}
    </>
  );
}