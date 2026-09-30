// frontend/widget/src/widget.js
(function () {
  "use strict";

  const LABELS = {
    active: { en: "GoC Verified Supplier", fr: "Fournisseur GC vérifié", color: "#16a34a" },
    revoked: { en: "Credential Revoked", fr: "Attestation révoquée", color: "#dc2626" },
    pending: { en: "Verification Pending", fr: "Vérification en attente", color: "#d97706" },
    not_found: { en: "Not Found", fr: "Introuvable", color: "#6b7280" },
  };

  function getLang() {
    return (navigator.language || "en").startsWith("fr") ? "fr" : "en";
  }

  function renderBadge(container, status) {
    const lang = getLang();
    // status is validated against the LABELS allowlist — only known keys produce content
    const info = LABELS[status] ?? LABELS.not_found;
    const span = document.createElement("span");
    span.setAttribute("role", "img");
    span.setAttribute("aria-label", info[lang]);
    span.style.cssText = [
      "display:inline-flex", "align-items:center", "gap:6px",
      `background:${info.color}`, "color:#fff", "border-radius:6px",
      "padding:6px 14px", "font-weight:700", "font-size:14px", "font-family:sans-serif",
    ].join(";");
    span.textContent = (status === "active" ? "✓ " : "✗ ") + info[lang];
    container.textContent = "";
    container.appendChild(span);
  }

  function renderError(container) {
    container.textContent = "";
  }

  async function init() {
    const scripts = document.querySelectorAll("script[data-bn]");
    scripts.forEach(async function (script) {
      const bn = script.getAttribute("data-bn");
      if (!bn) return;

      const apiBase = script.getAttribute("data-api") ?? "https://dstn.canada.ca";
      const container = document.createElement("div");
      container.setAttribute("data-dstn-badge", bn);
      script.parentNode.insertBefore(container, script.nextSibling);

      renderBadge(container, "pending");

      try {
        const r = await fetch(`${apiBase}/api/verify/${encodeURIComponent(bn)}`);
        if (!r.ok) throw new Error("API error");
        const data = await r.json();
        renderBadge(container, data.status ?? "not_found");
      } catch (_) {
        renderError(container);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
