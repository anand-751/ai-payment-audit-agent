import { useState } from "react";
import { T } from "./constants.js";
import { login } from "./auth.js";

export const Login = ({ onLogin }) => {
    const [role, setRole] = useState("ap");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [err, setErr] = useState(null);
    const [busy, setBusy] = useState(false);

    const go = async () => {
        if (!username || !password) {
            setErr("Please enter username and password.");
            return;
        }

        try {
            setBusy(true);
            setErr(null);

            const result = await login(
                username.trim(),
                password,
                role
            );

            if (result.ok) {
            onLogin(result.user);
            } else {
            setErr(
                result.error ||
                "Invalid credentials."
            );
            }
        } catch (error) {
            console.error(error);
            setErr("Authentication failed.");
        } finally {
            setBusy(false);
        }
    };


  return (
    <div
      style={{
        minHeight: "100vh",
        background: T.bg0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        position: "relative",
      }}
    >
      <style>{`
        /* Grid background */
        .login-grid {
          position: fixed; inset: 0;
          background-image:
            linear-gradient(${T.border} 1px, transparent 1px),
            linear-gradient(90deg, ${T.border} 1px, transparent 1px);
          background-size: 48px 48px;
          opacity: .18;
          pointer-events: none;
        }
        /* Radial glow */
        .login-glow {
          position: fixed; inset: 0;
          background: radial-gradient(ellipse 80% 60% at 50% 0%, ${T.cyan}12 0%, transparent 70%);
          pointer-events: none;
        }
        .li-input {
          background: ${T.bg2} !important;
          border: 1px solid ${T.border} !important;
          color: ${T.text0} !important;
          padding: 11px 14px;
          font-family: ${T.mono};
          font-size: 13px;
          outline: none;
          width: 100%;
          transition: border-color .2s, box-shadow .2s;
          border-radius: 2px;
        }
        .li-input:focus {
          border-color: ${T.cyan} !important;
          box-shadow: 0 0 0 2px ${T.cyan}20 !important;
        }
        .li-input::placeholder { color: ${T.text2}; }
        .login-btn {
          cursor: pointer;
          transition: all .2s;
          width: 100%;
          padding: 13px 0;
          background: linear-gradient(135deg, ${T.cyan}, ${T.violet});
          border: none;
          color: ${T.bg0};
          font-family: ${T.mono};
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 2px;
          border-radius: 2px;
        }
        .login-btn:hover:not(:disabled) {
          opacity: .9;
          transform: translateY(-1px);
          box-shadow: 0 8px 24px ${T.cyan}30;
        }
        .login-btn:disabled { opacity: .5; cursor: not-allowed; }
        .role-btn {
          cursor: pointer;
          transition: all .18s;
          padding: 10px 0;
          border: 1px solid;
          font-family: ${T.mono};
          font-size: 11px;
          letter-spacing: 1px;
          border-radius: 2px;
          background: transparent;
        }
        .role-btn:hover { filter: brightness(1.2); }
      `}</style>

      <div className="login-grid" />
      <div className="login-glow" />

      <div
        className="fu"
        style={{
          position: "relative",
          width: "min(520px, 92vw)",
          padding: "52px 52px 44px",
          background: `${T.bg1}E8`,
          border: `1px solid ${T.border2}`,
          backdropFilter: "blur(16px)",
          boxShadow: `0 40px 80px ${T.bg0}CC, 0 0 0 1px ${T.cyan}10`,
        }}
      >
        {/* Corner accents */}
        {[[0, 0], [0, 1], [1, 0], [1, 1]].map(([r, c], i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              top: r ? undefined : -1,
              bottom: r ? -1 : undefined,
              left: c ? undefined : -1,
              right: c ? -1 : undefined,
              width: 16,
              height: 16,
              borderTop: r ? "none" : `2px solid ${T.cyan}`,
              borderBottom: r ? `2px solid ${T.cyan}` : "none",
              borderLeft: c ? "none" : `2px solid ${T.cyan}`,
              borderRight: c ? `2px solid ${T.cyan}` : "none",
            }}
          />
        ))}

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div
            style={{
              display: "inline-block",
              fontFamily: T.mono,
              fontSize: 9,
              color: T.cyan,
              letterSpacing: 4,
              marginBottom: 10,
              padding: "3px 12px",
              border: `1px solid ${T.cyan}40`,
              background: T.cyanBg,
            }}
          >
            SECURE ACCESS
          </div>
          <div
            style={{
              fontSize: 28,
              fontWeight: 700,
              marginBottom: 6,
              background: `linear-gradient(135deg, ${T.text0}, ${T.cyan})`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Payment Control System
          </div>
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 11,
              color: T.text2,
              letterSpacing: 1,
            }}
          >
            AUTHORIZED PERSONNEL ONLY
          </div>
        </div>

        {/* Role Select */}
        <div style={{ marginBottom: 20 }}>
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 9,
              color: T.text2,
              letterSpacing: 2,
              marginBottom: 8,
            }}
          >
            SELECT ROLE
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {[
              ["ap", "AP MANAGER"],
              ["cfo", "CFO"],
            ].map(([r, l]) => (
              <button
                key={r}
                className="role-btn"
                onClick={() => {
                    setRole(r);
                    setErr(null);
                }}
                style={{
                  background:
                    role === r
                      ? r === "ap"
                        ? T.cyanBg
                        : T.violetBg
                      : "transparent",
                  borderColor:
                    role === r
                      ? r === "ap"
                        ? T.cyan
                        : T.violet
                      : T.border,
                  color:
                    role === r
                      ? r === "ap"
                        ? T.cyan
                        : T.violet
                      : T.text1,
                }}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        {/* Username */}
        <div style={{ marginBottom: 12 }}>
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 9,
              color: T.text2,
              letterSpacing: 2,
              marginBottom: 7,
            }}
          >
            USERNAME
          </div>
          <input
            className="li-input"
            type="text"
            placeholder="Enter username"
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
              setErr(null);
            }}
            onKeyDown={(e) => e.key === "Enter" && go()}
            autoComplete="username"
          />
        </div>

        {/* Password */}
        <div style={{ marginBottom: 6 }}>
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 9,
              color: T.text2,
              letterSpacing: 2,
              marginBottom: 7,
            }}
          >
            PASSWORD
          </div>
          <input
            className="li-input"
            type="password"
            placeholder="••••••••••"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setErr(null);
            }}
            onKeyDown={(e) => e.key === "Enter" && go()}
            autoComplete="current-password"
          />
          {err && (
            <div
              style={{
                fontFamily: T.mono,
                fontSize: 10,
                color: T.red,
                marginTop: 6,
              }}
            >
              ⚠ {err}
            </div>
          )}
        </div>


        <button className="login-btn" onClick={go} disabled={busy}>
          {busy ? "AUTHENTICATING..." : "AUTHENTICATE →"}
        </button>

        <div
          style={{
            marginTop: 16,
            fontFamily: T.mono,
            fontSize: 9,
            color: T.text2,
            textAlign: "center",
            letterSpacing: 1,
          }}
        >
          Session encrypted · All actions logged · JWT authenticated
        </div>
      </div>
    </div>
  );
};