import { T } from "./constants.js";

export const TopBar = ({
  user,
  onBack,
  showBack,
  notifications = [],
  showNotifications,
  onOpenNotifications,
  onViewHistory,
  onLogout,
}) => {
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div
      style={{
        background: `${T.bg1}F0`,
        backdropFilter: "blur(12px)",
        borderBottom: `1px solid ${T.border}`,
      padding: "0 40px",
      height: 60,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      {/* LEFT */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        {showBack && (
          <button
            onClick={onBack}
            className="hov-btn"
            style={{
              fontFamily: T.mono,
              fontSize: 10,
              color: T.text1,
              border: `1px solid ${T.border}`,
              background: "transparent",
              padding: "4px 10px",
              letterSpacing: 1,
            }}
          >
            ← BACK
          </button>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Animated status dot */}
          <div style={{ position: "relative" }}>
            <div
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: T.green,
                boxShadow: `0 0 10px ${T.green}`,
                animation: "glowPulse 2.5s ease-in-out infinite",
              }}
            />
          </div>
          <span
            style={{
              fontFamily: T.mono,
              fontSize: 10,
              color: T.text2,
              letterSpacing: 2,
            }}
          >
            SECURE FINANCE CONTROLLER PORTAL
          </span>
          {/* Role badge */}
          <span
            style={{
              fontFamily: T.mono,
              fontSize: 8,
              color: user?.role === "ap" ? T.cyan : T.violet,
              border: `1px solid ${user?.role === "ap" ? T.cyan + "50" : T.violet + "50"}`,
              background: user?.role === "ap" ? T.cyanBg : T.violetBg,
              padding: "2px 8px",
              letterSpacing: 1.5,
            }}
          >
            {user?.role === "ap" ? "AP MGR" : "CFO"}
          </span>
        </div>
      </div>

      {/* RIGHT */}
      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        {/* Bell — AP only */}
        {user?.role === "ap" && (
          <div
            onClick={onOpenNotifications}
            style={{
              position: "relative",
              cursor: "pointer",
              fontSize: 16,
              userSelect: "none",
              color: T.text1,
            }}
          >
            🔔
            {showNotifications && (
              <div
                style={{
                  position: "absolute",
                  top: 30,
                  right: 0,
                  width: 300,
                  background: T.bg1,
                  border: `1px solid ${T.border2}`,
                  padding: "14px",
                  zIndex: 999,
                  boxShadow: `0 20px 40px ${T.bg0}CC`,
                }}
              >
                <div
                  style={{
                    fontFamily: T.mono,
                    fontSize: 9,
                    color: T.cyan,
                    letterSpacing: 2,
                    marginBottom: 12,
                  }}
                >
                  NOTIFICATIONS
                </div>
                {notifications.length === 0 ? (
                  <div
                    style={{
                      fontFamily: T.mono,
                      fontSize: 10,
                      color: T.text2,
                    }}
                  >
                    No rejected batches yet.
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      style={{
                        padding: "9px 0",
                        borderBottom: `1px solid ${T.border}`,
                      }}
                    >
                        <div
                            style={{
                                fontFamily: T.mono,
                                fontSize: 10,
                                color: T.text0,
                                marginBottom: 4,
                            }}
                            >
                            {n.file || n.file_name}
                            </div>

                            <div
                            style={{
                                fontFamily: T.mono,
                                fontSize: 9,
                                color: T.red,
                            }}
                            >
                            Rejected by CFO
                        </div>
                    </div>
                  ))
                )}
                <div style={{ marginTop: 12 }}>
                  <button
                    onClick={onViewHistory}
                    style={{
                      width: "100%",
                      padding: "8px",
                      background: T.cyanBg,
                      border: `1px solid ${T.cyanDim}`,
                      color: T.cyan,
                      fontFamily: T.mono,
                      fontSize: 10,
                      cursor: "pointer",
                      letterSpacing: 1,
                    }}
                  >
                    VIEW HISTORY
                  </button>
                </div>
              </div>
            )}

            {unreadCount > 0 && (
              <span
                style={{
                  position: "absolute",
                  top: -6,
                  right: -10,
                  minWidth: 18,
                  height: 18,
                  borderRadius: "50%",
                  background: T.red,
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: T.mono,
                  fontSize: 9,
                  fontWeight: 600,
                  padding: "0 4px",
                }}
              >
                {unreadCount}
              </span>
            )}
          </div>
        )}

        <span
          style={{ fontFamily: T.mono, fontSize: 10, color: T.text2 }}
        >
          {user?.name?.toUpperCase()}
        </span>

        {/* <button
          onClick={onSwitch}
          className="hov-btn"
          style={{
            fontFamily: T.mono,
            fontSize: 10,
            color: T.cyan,
            border: `1px solid ${T.cyanDim}`,
            background: T.cyanBg,
            padding: "4px 12px",
            letterSpacing: 1,
          }}
        >
          SWITCH ROLE
        </button> */}

        <button
          onClick={onLogout}
          className="hov-btn"
          style={{
            fontFamily: T.mono,
            fontSize: 10,
            color: T.text2,
            border: `1px solid ${T.border}`,
            background: "transparent",
            padding: "4px 10px",
            letterSpacing: 1,
          }}
        >
          LOGOUT
        </button>
      </div>
    </div>
  );
};