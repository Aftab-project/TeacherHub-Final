// =============================================================================
// script.js — Teacher Feature Hub Home Page
// =============================================================================
// This file powers the main dashboard (index.html).
// It does two things:
//   1. Builds the feature card grid by reading the `features` array and
//      creating a clickable <a> card element for each entry.
//   2. Runs a live search filter so teachers can quickly find a feature
//      by typing into the search box.
//
// To add a new feature to the hub, just add one object to the `features`
// array below — no other code changes are needed.
// =============================================================================

// ── Feature data ──────────────────────────────────────────────────────────────
// Each object describes one feature card that appears on the home page.
// Properties:
//   name        — Heading text shown on the card.
//   description — Short sentence describing what the feature does.
//   icon        — HTML entity for an emoji shown at the top of the card.
//   link        — URL or relative path the card links to when clicked.

const features = [
  {
    name: "Student Mental Health",
    description: "Monitor wellbeing indicators and keep simple support notes for students.",
    icon: "&#129504;",
    link: "mental-health/index.html"
  },
  {
    name: "Face Recognition Attendance",
    description: "Use camera-based recognition to mark attendance faster and reduce manual errors.",
    icon: "&#128100;",
    link: "face-attendance/index.html"
  },
  {
    name: "UniCommunication",
    description: "Teacher communication area for team chat, private chat, video calls, files, and tasks.",
    icon: "&#128172;",
    link: "http://127.0.0.1:5000/team-com/" // Team Com runs as a separate Flask server.
  }
];

// ── DOM references ────────────────────────────────────────────────────────────
// Grab the HTML elements we need to interact with.

// The <section> that will contain all the generated feature cards.
const grid = document.getElementById("featureGrid");

// The search <input> at the top of the page.
const featureSearch = document.getElementById("featureSearch");

// The status paragraph below the grid that tells the teacher how many
// features are showing (used for screen readers via aria-live too).
const featureSearchStatus = document.getElementById("featureSearchStatus");

// ── Build feature cards ───────────────────────────────────────────────────────
// Loop over every feature object and create an <a> element for each one.
// Using <a> instead of <div> means the card is natively keyboard-accessible
// (you can Tab to it and press Enter to follow the link).

features.forEach((feature) => {
  const card = document.createElement("a");
  card.className = "feature-card";       // CSS class that styles the card.
  card.href = feature.link;              // Where clicking the card goes.

  // Store a lowercase version of the name for fast searching.
  // The filterFeatureCards() function compares the search query against this.
  card.dataset.search = feature.name.toLowerCase();

  // Build the card's inner HTML using a template literal.
  // aria-hidden="true" on the icon means screen readers skip the emoji
  // and read the meaningful heading instead.
  card.innerHTML = `
    <div class="card-body">
      <div class="icon-wrap" aria-hidden="true">${feature.icon}</div>
      <h2>${feature.name}</h2>
      <span class="card-arrow" aria-hidden="true">&#8594;</span>
    </div>
  `;

  // Add the finished card to the grid section in the HTML.
  grid.appendChild(card);
});

// ── Set current year in footer ────────────────────────────────────────────────
// Keeps the copyright year in the footer accurate without manual updates.
const yearElement = document.getElementById("currentYear");
yearElement.textContent = new Date().getFullYear();

// ── Search / filter logic ─────────────────────────────────────────────────────

/**
 * filterFeatureCards(query)
 * Shows only the cards whose name or description contains the search query.
 * Cards that don't match are hidden with display:none.
 * The status paragraph is updated to say how many results are visible.
 *
 * @param {string} query - The raw text the teacher typed into the search box.
 */
function filterFeatureCards(query) {
  // Normalise: strip surrounding spaces and make lowercase for comparison.
  const normalized = query.trim().toLowerCase();

  // Collect all the card elements that were added to the grid.
  const cards = [...grid.querySelectorAll(".feature-card")];
  let visibleCount = 0;

  cards.forEach((card) => {
    // data-search holds the pre-lowercased name + description string.
    const shouldShow = card.dataset.search.includes(normalized);

    // Show or hide this card based on whether it matches.
    card.style.display = shouldShow ? "" : "none";

    if (shouldShow) {
      visibleCount += 1;
    }
  });

  // Update the status text so the teacher knows how many results are showing.
  featureSearchStatus.textContent =
    visibleCount === features.length
      ? "Showing all features."
      : `Showing ${visibleCount} feature(s).`;
}

// Listen for every keystroke in the search box and re-filter immediately.
featureSearch.addEventListener("input", (event) => {
  filterFeatureCards(event.target.value);
});

// Run the filter once on page load with an empty query → shows all cards
// and sets the status text to "Showing all features."
filterFeatureCards("");
