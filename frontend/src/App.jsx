import { useState, useEffect } from "react";

// ── Utils & constants ──────────────────────────────────────────────
import { getSession, logout } from "./components/auth";

// ── Components ─────────────────────────────────────────────────────
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

  // ── Load batches from the backend DB (this is what was missing) ─────────────
  // Merges server data (source of truth, incl. status) with any in-memory audit
  // detail (metadata/violations) we already have from this session's uploads.
  const fetchBatches = async () => {
    try {
      const res = await fetch(`${API_BASE}/batches`);
      if (!res.ok) return;
      const data = await res.json();
      const serverBatches = data.batches || [];
      setBatches((prev) => {
        const detailById = Object.fromEntries(prev.map((b) => [b.id, b]));
        return serverBatches.map((sb) => ({ ...detailById[sb.id], ...sb }));
      });
    } catch (err) {
      console.error("Failed to load batches", err);
    }
  };

  // ── Load notifications for the current role (CFO sees new-batch alerts,
  //    AP sees approved/rejected alerts). Backend-driven so it works cross-device.
  const fetchNotifications = async () => {
    try {
      const res = await fetch(
        `${API_BASE}/notifications?role=${user.role}&user=${encodeURIComponent(
          user.username
        )}`
      );
      if (!res.ok) return;
      const data = await res.json();
      setNotifications(
        (data.data || []).map((n) => ({
          id: n.notification_id,
          batchNo: n.batch_id,
          file: n.batch_id,
          decision: n.decision,
          message: n.message || n.title,
          is_read: !!n.is_read,
          createdAt: n.created_at,
        }))
      );
    } catch (err) {
      console.error("Failed to load notifications", err);
    }
  };

  // Poll so AP uploads appear for the CFO automatically (no re-login needed)
  useEffect(() => {
    if (!user) return;
    fetchBatches();
    fetchNotifications();
    const id = setInterval(() => {
      fetchBatches();
      fetchNotifications();
    }, 5000);
    return () => clearInterval(id);
  }, [user]);

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
    // Send the logged-in AP user so the CFO can see who uploaded, and so a
    // decision notification is routed back to THIS uploader specifically.
    formData.append("uploaded_by", user.username);
    formData.append("uploaded_by_name", user.name);

    const uploadRes = await fetch(`${API_BASE}/upload-payment-batch`, {
      method: "POST",
      body: formData,
    });

    const uploadData = await uploadRes.json();
    if (!uploadRes.ok) {
      throw new Error(
        uploadData.detail || uploadData.message || "Failed to upload batch."
      );
    }

    const uploadedBatches = uploadData.data;

    for (const uploaded of uploadedBatches) {
      const batchId = uploaded.batch_id;
      const auditRes = await fetch(`${API_BASE}/run-audit/${batchId}`, {
        method: "POST",
      });
      const auditData = await auditRes.json();
      if (!auditRes.ok) {
        throw new Error(
          auditData.detail || auditData.message || "Failed to run audit."
        );
      }
    }

    // Pull fresh truth from the backend so the new batch(es) show up everywhere
    await fetchBatches();
  };

  // ── Open a batch: use in-memory detail if present, else load from backend ────
  const handleSelectBatch = async (batch) => {
    if (batch.metadata && batch.violations) {
      setSelectedBatch(batch);
      return;
    }
    try {
      // NOTE: add this GET endpoint on the backend (see chat notes).
      const res = await fetch(`${API_BASE}/batch/${batch.id}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedBatch({ ...batch, ...data });
        return;
      }
    } catch (err) {
      console.error("Failed to load batch detail", err);
    }
    // Safe fallback so the UI never crashes if detail isn't available yet
    setSelectedBatch({
      ...batch,
      metadata: {
        batch_id: batch.id,
        integrity_score: batch.integrityScore ?? 100,
      },
      violations: [],
      cfo_summary: "Detail endpoint not available yet.",
    });
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

    // Optimistic update, then re-sync with the backend
    setBatches((prev) =>
      prev.map((b) => (b.id === batch.id ? { ...b, status: finalDecision } : b))
    );
    fetchBatches();
    fetchNotifications();

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
    // Persist read-state to the backend so the badge stays cleared after refresh
    notifications
      .filter((n) => !n.is_read)
      .forEach((n) => {
        fetch(`${API_BASE}/notifications/${n.id}/read`, { method: "POST" }).catch(
          () => {}
        );
      });
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
        <CFOBatchList batches={batches} onSelect={handleSelectBatch} />
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




// import { useState, useEffect } from "react";

// // ── Utils & constants ──────────────────────────────────────────────────────────
// import { getSession, logout } from "./components/auth";

// // ── Components ─────────────────────────────────────────────────────────────────
// import { GlobalStyles } from "./components/GlobalStyles";
// import { TopBar } from "./components/TopBar";
// import { Login } from "./components/Login";
// import { APPortal } from "./components/APPortal";
// import { CFOBatchList } from "./components/CFOBatchList";
// import { CFODashboard } from "./components/CFODashboard";
// import { HistoryModal } from "./components/HistoryModal";

// const API_BASE = "/api";

// export default function App() {
//   const [user, setUser] = useState(() => getSession());

//   const [batches, setBatches] = useState([]);
//   const [selectedBatch, setSelectedBatch] = useState(null);
//   const [notifications, setNotifications] = useState([]);
//   const [showNotifications, setShowNotifications] = useState(false);
//   const [historyRows, setHistoryRows] = useState([]);
//   const [showHistory, setShowHistory] = useState(false);

//   useEffect(() => {
//     const session = getSession();
//     if (session) setUser(session);
//   }, []);

//   const handleLogin = (userPayload) => {
//     setUser(userPayload);
//   };

//   const handleLogout = () => {
//     logout();
//     setUser(null);
//     setSelectedBatch(null);
//   };

//   const handleUpload = async (files) => {

//     const formData = new FormData();

//     files.forEach((file) => {
//       formData.append("files", file);
//     });

//     const uploadRes = await fetch(
//       `${API_BASE}/upload-payment-batch`,
//       {
//         method: "POST",
//         body: formData,
//       }
//     );

//     const uploadData = await uploadRes.json();

//     if (!uploadRes.ok) {
//       throw new Error(
//         uploadData.detail ||
//         uploadData.message ||
//         "Failed to upload batch."
//       );
//     }

//     const uploadedBatches = uploadData.data;

//     const createdBatches = [];

//     for (const uploaded of uploadedBatches) {

//       const batchId = uploaded.batch_id;

//       const auditRes = await fetch(
//         `${API_BASE}/run-audit/${batchId}`,
//         {
//           method: "POST",
//         }
//       );

//       const auditData = await auditRes.json();

//       if (!auditRes.ok) {
//         throw new Error(
//           auditData.detail ||
//           auditData.message ||
//           "Failed to run audit."
//         );
//       }

//       const result = auditData.data;

//       createdBatches.push({
//         id: batchId,
//         file: uploaded.file_name,
//         uploadedBy: user.name,
//         uploadedAt: new Date().toISOString(),
//         status: result.metadata.decision || "UNDER_REVIEW",
//         payments: uploaded.batch_info.total_items,
//         total: uploaded.batch_info.total_amount,
//         integrityScore: result.metadata.integrity_score ?? 0,
//         redFlags: result.metadata.red_flags ?? 0,
//         yellowFlags: result.metadata.yellow_flags ?? 0,
//         highRiskExposure:
//           result.metadata.high_risk_exposure ?? 0,
//         blockedCount:
//           result.metadata.total_blocked_payments ?? 0,
//         metadata: result.metadata,
//         violations: result.violations || [],
//         cfo_summary:
//           result.cfo_summary ||
//           "Audit completed.",
//       });
//     }

//     setBatches((prev) => [
//       ...createdBatches,
//       ...prev,
//     ]);
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
//       prev.map((b) => (b.id === batch.id ? { ...b, status: finalDecision } : b))
//     );

//     if (decision === "REJECT") {
//       setNotifications((prev) => [
//         {
//           id: Date.now(),
//           batchNo: batch.id,
//           file: batch.file,
//           decision: "REJECTED",
//           message: "Rejected by CFO",
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

//       {user.role === "ap" && (
//         <APPortal batches={batches} onUpload={handleUpload} />
//       )}

//       {user.role === "cfo" && !selectedBatch && (
//         <CFOBatchList batches={batches} onSelect={setSelectedBatch} />
//       )}

//       {user.role === "cfo" && selectedBatch && (
//         <CFODashboard
//           batch={selectedBatch}
//           user={user}
//           apiBase={API_BASE}
//           onBack={() => setSelectedBatch(null)}
//           onDecision={handleDecision}
//         />
//       )}

//       {showHistory && (
//         <HistoryModal rows={historyRows} onClose={() => setShowHistory(false)} />
//       )}
//     </>
//   );
// }