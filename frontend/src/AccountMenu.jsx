// The account chip at the foot of the sidebar, and the menu it opens.
// Asked for 2026-09-15 with ChatGPT's sidebar as the reference: an avatar with
// the name and what kind of account it is, opening upward into everything that
// used to be a loose row of links.
//
// The menu holds what the dark banner used to: the guides, the lab-only pages,
// the admin link, and the way in or out. Keyboard and outside-click handling
// follow ConstructPicker, which is the house pattern for a popup.
import { useEffect, useRef, useState } from "react";

const ROLE_LABELS = {
  external: "External user",
  lab: "Lab member",
  maintainer: "Maintainer",
  pi: "Principal investigator",
};

// "Deva Anand" -> "DA"; "mohammad" -> "M". Two letters at most, because three
// stop being legible at 26px.
function initials(name) {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "";
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function Icon({ d, circle }) {
  return (
    <svg
      className="menu-icon" width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true"
    >
      {circle && <circle cx="12" cy="12" r="9" />}
      <path d={d} />
    </svg>
  );
}

const ICONS = {
  about: <Icon circle d="M12 11v5M12 8h.01" />,
  guide: <Icon d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5zM20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5z" />,
  testing: <Icon d="M9 3v6l-5 9a2 2 0 0 0 1.8 3h12.4a2 2 0 0 0 1.8-3l-5-9V3M8 3h8" />,
  product: <Icon d="M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12L4 7.5" />,
  admin: <Icon d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" />,
  signout: <Icon d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4M16 16l4-4-4-4M20 12H10" />,
  signin: <Icon d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4M10 16l-4-4 4-4M6 12h10" />,
};

export default function AccountMenu({ auth, onAbout, onSignIn, onSignOut }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const buttonRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key !== "Escape") return;
      // Stop here: the drawer also closes on Escape, and dismissing both with
      // one key would leave you looking at a workspace you did not ask for.
      e.stopPropagation();
      setOpen(false);
      buttonRef.current?.focus();
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey, true);
    };
  }, [open]);

  const signedIn = !!auth?.signed_in;
  const name = signedIn ? auth.name : "Not signed in";
  // The line under the name is ChatGPT's plan slot. Ours says what kind of
  // account this is, which is the thing that changes what you can do here.
  const subtitle = signedIn
    ? ROLE_LABELS[auth.role] || "Account"
    : "Sign in to keep your work";

  const run = (fn) => () => {
    setOpen(false);
    fn?.();
  };

  return (
    <div className="account" ref={rootRef}>
      {open && (
        <div className="account-menu" role="menu" aria-label="Account and links">
          <div className="account-menu-head">
            <span className={"avatar" + (signedIn ? "" : " avatar-anon")} aria-hidden="true">
              {signedIn ? initials(auth.name) : "?"}
            </span>
            <span className="account-menu-id">
              <b>{name}</b>
              <span className="small muted">{signedIn ? auth.email : subtitle}</span>
            </span>
          </div>

          <div className="account-menu-items">
            <button className="menu-item" role="menuitem" onClick={run(onAbout)}>
              {ICONS.about} About this platform
            </button>
            <a className="menu-item" role="menuitem" href="/guide">
              {ICONS.guide} Guide
            </a>
            {/* /testing and /product are lab-internal; the server enforces the
                gate, the menu just does not advertise them to everyone else. */}
            {["lab", "maintainer", "pi"].includes(auth?.role) && (
              <>
                <a className="menu-item" role="menuitem" href="/testing">
                  {ICONS.testing} Testing guide
                </a>
                <a className="menu-item" role="menuitem" href="/product">
                  {ICONS.product} How it works
                </a>
              </>
            )}
            {auth?.is_admin && (
              <a className="menu-item" role="menuitem" href="/admin">
                {ICONS.admin} Admin
              </a>
            )}
          </div>

          <div className="account-menu-items account-menu-end">
            {signedIn ? (
              <button className="menu-item" role="menuitem" onClick={run(onSignOut)}>
                {ICONS.signout} Sign out
              </button>
            ) : (
              <button className="menu-item" role="menuitem" onClick={run(onSignIn)}>
                {ICONS.signin} Sign in or create an account
              </button>
            )}
          </div>
        </div>
      )}

      <button
        className="account-chip"
        ref={buttonRef}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className={"avatar" + (signedIn ? "" : " avatar-anon")} aria-hidden="true">
          {signedIn ? initials(auth.name) : "?"}
        </span>
        <span className="account-chip-id">
          <b>{name}</b>
          <span className="account-chip-sub">{subtitle}</span>
        </span>
        <svg
          className="account-chip-caret" width="14" height="14" viewBox="0 0 24 24"
          fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
          strokeLinejoin="round" aria-hidden="true"
        >
          <path d="M8 9l4-4 4 4M8 15l4 4 4-4" />
        </svg>
      </button>
    </div>
  );
}
