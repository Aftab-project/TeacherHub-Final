// =============================================================================
// auth.js — Shared Authentication Module
// =============================================================================
// This file handles login, logout, and access control for the entire
// Teacher Feature Hub. Every page loads this file and calls requireAuth()
// at the top of its own <script> block so only logged-in teachers can view it.
//
// HOW IT WORKS:
//   1. The teacher visits any page.
//   2. requireAuth() checks localStorage for the "logged in" flag.
//   3. If not logged in → redirect to login.html.
//   4. On login.html, loginWithPasscode() validates the passcode.
//   5. On success, the flag is saved → teacher is redirected back.
//   6. The logout button calls logout() → clears the flag → back to login.
// =============================================================================

// ── Storage keys & passcode ───────────────────────────────────────────────────

// The key used to store the login flag in localStorage and in a cookie.
const HUB_AUTH_KEY = "teacherFeatureHubAuth";

// The passcode teachers must enter to log in. Change this to update access.
const HUB_PASSCODE = "TFH2026";

// Cookie name mirrors the localStorage key so both stay in sync.
const HUB_AUTH_COOKIE = "teacherFeatureHubAuth";

// ── Core functions ────────────────────────────────────────────────────────────

/**
 * isAuthenticated()
 * Returns true if the teacher is currently logged in.
 * Checks localStorage for the saved login flag.
 * Used by requireAuth() and by login.html to skip the login screen.
 */
function isAuthenticated() {
  return localStorage.getItem(HUB_AUTH_KEY) === "true";
}

/**
 * requireAuth(rootPath)
 * Call this at the top of every protected page's script.
 * If the teacher is NOT logged in, they are immediately redirected
 * to the login page. The current URL is passed as ?next= so that
 * after login they land back on the page they tried to visit.
 *
 * @param {string} rootPath - Relative path back to the hub root (e.g. "../").
 *                            This tells the redirect where login.html lives.
 */
function requireAuth(rootPath) {
  // If already logged in, do nothing — let the page load normally.
  if (isAuthenticated()) {
    return;
  }

  // Capture the current page path so we can redirect back after login.
  const nextPath = window.location.pathname;
  window.location.href = `${rootPath}login.html?next=${encodeURIComponent(nextPath)}`;
}

/**
 * loginWithPasscode(passcode)
 * Validates the passcode entered on login.html.
 * On success: saves the login flag to localStorage and a cookie, returns true.
 * On failure: returns false without changing anything.
 *
 * The cookie (max-age=86400 = 24 hours) is set alongside localStorage as a
 * belt-and-braces approach — some server environments check cookies.
 *
 * @param {string} passcode - The passcode string typed by the teacher.
 * @returns {boolean} true if the passcode matched, false otherwise.
 */
function loginWithPasscode(passcode) {
  if (passcode === HUB_PASSCODE) {
    // Save login flag to localStorage so it persists across tabs.
    localStorage.setItem(HUB_AUTH_KEY, "true");
    // Also set a cookie that expires after 24 hours (86400 seconds).
    document.cookie = `${HUB_AUTH_COOKIE}=true; path=/; max-age=86400; SameSite=Lax`;
    return true;
  }

  return false;
}

/**
 * logout()
 * Clears all login state from both localStorage and the cookie.
 * After this, isAuthenticated() returns false and every page will
 * redirect back to login.html on the next visit.
 */
function logout() {
  localStorage.removeItem(HUB_AUTH_KEY);
  // Setting max-age=0 immediately expires and deletes the cookie.
  document.cookie = `${HUB_AUTH_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

/**
 * setupLogoutButton()
 * Finds the element with id="logoutButton" on the current page and
 * attaches a click handler that logs out and redirects to login.html.
 *
 * The button's data-root attribute tells us how many levels up login.html is
 * (e.g. data-root="../" for pages inside a sub-folder).
 *
 * Call this once on each page that has a logout button.
 */
function setupLogoutButton() {
  const logoutButton = document.getElementById("logoutButton");

  // If this page has no logout button, there is nothing to set up.
  if (!logoutButton) {
    return;
  }

  logoutButton.addEventListener("click", () => {
    // Read the root path from the button's HTML attribute, defaulting to "./".
    const rootPath = logoutButton.dataset.root || "./";
    logout();
    window.location.href = `${rootPath}login.html`;
  });
}

// ── Expose functions globally ─────────────────────────────────────────────────
// These assignments make the functions accessible from inline <script> blocks
// in HTML files (e.g. requireAuth("../"); in a <script> tag on a feature page).

window.isAuthenticated = isAuthenticated;
window.requireAuth = requireAuth;
window.loginWithPasscode = loginWithPasscode;
window.setupLogoutButton = setupLogoutButton;
window.logoutTeacherHub = logout; // Alias kept for any external reference.
