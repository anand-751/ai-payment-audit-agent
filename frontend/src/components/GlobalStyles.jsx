// import { T } from "./constants.js";

// export const GlobalStyles = () => (
//   <style>{`
//     @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Inter:wght@300;400;500;600;700&display=swap');

//     *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
//     html, body, #root { min-height: 100%; background: ${T.bg0}; }
//     body {
//       background: ${T.bg0};
//       color: ${T.text0};
//       font-family: ${T.sans};
//       -webkit-font-smoothing: antialiased;
//     }

//     ::-webkit-scrollbar { width: 4px; }
//     ::-webkit-scrollbar-track { background: ${T.bg1}; }
//     ::-webkit-scrollbar-thumb { background: ${T.border2}; border-radius: 2px; }

//     input[type=file] { display: none; }
//     textarea { resize: none; outline: none; }

//     @keyframes fadeUp {
//       from { opacity: 0; transform: translateY(12px); }
//       to   { opacity: 1; transform: translateY(0); }
//     }
//     @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
//     @keyframes scanline {
//       0%   { transform: translateY(-100%); }
//       100% { transform: translateY(100vh); }
//     }
//     @keyframes glowPulse {
//       0%,100% { box-shadow: 0 0 8px ${T.cyan}40; }
//       50%     { box-shadow: 0 0 20px ${T.cyan}80, 0 0 40px ${T.cyan}20; }
//     }
//     @keyframes borderGlow {
//       0%,100% { border-color: ${T.cyanDim}; }
//       50%     { border-color: ${T.cyan}; }
//     }

//     .fu  { animation: fadeUp .4s ease both; }
//     .s1  { animation-delay: .04s; }
//     .s2  { animation-delay: .08s; }
//     .s3  { animation-delay: .12s; }
//     .s4  { animation-delay: .16s; }
//     .s5  { animation-delay: .20s; }

//     .hov-row { transition: background .15s; cursor: pointer; }
//     .hov-row:hover { background: ${T.bg3} !important; }

//     .hov-btn { transition: all .18s; cursor: pointer; }
//     .hov-btn:hover { filter: brightness(1.2); transform: translateY(-1px); }

//     .filter-btn { transition: all .15s; cursor: pointer; }
//     .filter-btn:hover { border-color: ${T.cyan} !important; color: ${T.cyan} !important; }

//     textarea:focus { border-color: ${T.cyanDim} !important; }

//     .glow-cyan { animation: glowPulse 2.5s ease-in-out infinite; }

//     /* Noise overlay */
//     .noise::after {
//       content: '';
//       position: fixed;
//       inset: 0;
//       background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.03'/%3E%3C/svg%3E");
//       pointer-events: none;
//       z-index: 9999;
//     }
//   `}</style>
// );



import { T } from "./constants.js";

export const GlobalStyles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Inter:wght@300;400;500;600;700&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { min-height: 100%; background: ${T.bg0}; }
    #root { min-height: 100vh; width: 100%; background: ${T.bg0}; }
    body {
      background: ${T.bg0};
      color: ${T.text0};
      font-family: ${T.sans};
      -webkit-font-smoothing: antialiased;
    }

    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: ${T.bg0}; }
    ::-webkit-scrollbar-thumb { background: ${T.border2}; border-radius: 4px; }

    input[type=file] { display: none; }
    textarea { resize: none; outline: none; }

    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(10px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
    @keyframes glowPulse {
      0%,100% { box-shadow: 0 0 0 3px ${T.cyan}20; }
      50%     { box-shadow: 0 0 0 5px ${T.cyan}35; }
    }
    @keyframes borderGlow {
      0%,100% { border-color: ${T.cyanDim}80; }
      50%     { border-color: ${T.cyanDim}; }
    }

    .fu  { animation: fadeUp .35s ease both; }
    .s1  { animation-delay: .04s; }
    .s2  { animation-delay: .08s; }
    .s3  { animation-delay: .12s; }
    .s4  { animation-delay: .16s; }
    .s5  { animation-delay: .20s; }

    /* Row hover — light fill, clear contrast maintained */
    .hov-row { transition: background .12s; cursor: pointer; }
    .hov-row:hover { background: ${T.bg3} !important; }

    /* Button hover — subtle lift + shadow */
    .hov-btn { transition: all .18s; cursor: pointer; }
    .hov-btn:hover {
      filter: brightness(1.04);
      transform: translateY(-1px);
      box-shadow: 0 4px 14px rgba(55,48,163,0.12);
    }

    .filter-btn { transition: all .15s; cursor: pointer; }
    .filter-btn:hover {
      border-color: ${T.cyan} !important;
      color: ${T.cyan} !important;
      background: ${T.cyanBg} !important;
    }

    textarea:focus {
      border-color: ${T.cyanDim} !important;
      box-shadow: 0 0 0 3px ${T.cyan}18 !important;
    }

    /* Status dot pulse in TopBar — uses green which is readable */
    .glow-cyan { animation: glowPulse 2.8s ease-in-out infinite; }

    /* Page-level card shadow utility */
    .card-shadow {
      box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    }
  `}</style>
);