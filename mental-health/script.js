// =============================================================================
// mental-health/script.js — Wellbeing Log Tracker
// =============================================================================
// NOTE: This script is NOT linked from mental-health/index.html.
// The current mental health page uses a Chatbase AI chatbot embedded via an
// <iframe> instead of this local form-based tracker.
//
// This script is kept for reference. It implements a fully working wellbeing
// log that stores entries in localStorage. If you want to switch from the
// chatbot to the local form tracker in the future:
//   1. Replace the iframe in index.html with the form HTML.
//   2. Add <script src="script.js"></script> at the bottom of index.html.
//
// WHAT THIS SCRIPT DOES:
//   - Lets the teacher log a student's mood level, concern level, and note.
//   - Saves all log entries to localStorage.
//   - Renders them in a scrollable list, newest first.
//   - Calculates summary stats (total checks, high concern count, low mood count).
//   - Supports date-range filtering, CSV export, demo data seeding, and printing.
// =============================================================================

// ── localStorage Key ──────────────────────────────────────────────────────────
// All wellbeing log entries are stored under this key. The prefix ensures it
// doesn't conflict with other features that also use localStorage.
const STORAGE_KEY = "teacherFeatureHubMentalHealth";

// ── DOM References ────────────────────────────────────────────────────────────
// Point to the HTML elements used by this script. These would need to exist in
// the HTML page for this script to work.

const wellbeingForm          = document.getElementById("wellbeingForm");
const mentalList             = document.getElementById("mentalList");
const mentalStatus           = document.getElementById("mentalStatus");
const clearMentalLogButton   = document.getElementById("clearMentalLog");
const exportMentalCsvButton  = document.getElementById("exportMentalCsv");
const seedMentalDemoButton   = document.getElementById("seedMentalDemo");
const mentalStartDate        = document.getElementById("mentalStartDate");
const mentalEndDate          = document.getElementById("mentalEndDate");
const applyMentalFilterButton = document.getElementById("applyMentalFilter");
const resetMentalFilterButton = document.getElementById("resetMentalFilter");
const printMentalReportButton = document.getElementById("printMentalReport");
const totalChecks            = document.getElementById("totalChecks");
const highConcernCount       = document.getElementById("highConcernCount");
const lowMoodCount           = document.getElementById("lowMoodCount");

// ── CSV Helpers ───────────────────────────────────────────────────────────────

/**
 * csvCell(value)
 * Wraps a value in double quotes and escapes any internal double quotes for CSV.
 */
function csvCell(value) {
  return `"${String(value).replace(/"/g, '""')}"`;
}

/**
 * downloadCsv(filename, rows)
 * Creates a CSV file from a 2D array and triggers a browser download.
 * rows[0] is the header row; the rest are data rows.
 *
 * @param {string}   filename - The name for the downloaded file.
 * @param {string[][]} rows   - 2D array of string values.
 */
function downloadCsv(filename, rows) {
  const csvData = rows.map((row) => row.map(csvCell).join(",")).join("\n");
  const blob    = new Blob([csvData], { type: "text/csv;charset=utf-8;" });
  const link    = document.createElement("a");
  link.href     = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

// ── Storage Helpers ─────────────────────────────────────────────────────────────────

/**
 * getEntries()
 * Reads all saved wellbeing log entries from localStorage.
 * Returns an empty array if nothing has been saved yet.
 *
 * @returns {object[]} Array of entry objects.
 */
function getEntries() {
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : [];
}

/**
 * saveEntries(entries)
 * Serialises the entire entries array to localStorage as a JSON string.
 * Overwrites the previous value every time (full save, not append).
 *
 * @param {object[]} entries - The complete array of entry objects to save.
 */
function saveEntries(entries) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

// ── Date / Timestamp Helpers ─────────────────────────────────────────────────────

/**
 * formatDate(timestamp)
 * Converts a Unix timestamp (milliseconds) to a human-readable date/time string.
 * Example: formatDate(1718300000000) returns "13/06/2026, 14:33:20"
 *
 * @param {number} timestamp - Milliseconds since the Unix epoch.
 * @returns {string} Locale-formatted date and time string.
 */
function formatDate(timestamp) {
  return new Date(timestamp).toLocaleString();
}

/**
 * parseEntryTimestamp(entry)
 * Returns the numeric timestamp for a log entry.
 * Entries created by newer code have a `timestamp` property (milliseconds).
 * Older entries only have a `date` string, so we parse that as a fallback.
 * If parsing fails, returns the current time (a safe but imprecise fallback).
 *
 * @param {object} entry - A wellbeing log entry object.
 * @returns {number} The entry's timestamp in milliseconds.
 */
function parseEntryTimestamp(entry) {
  if (entry.timestamp) {
    return Number(entry.timestamp);
  }

  const parsed = Date.parse(entry.date);
  return Number.isNaN(parsed) ? Date.now() : parsed;
}

/**
 * getFilteredEntries(entries)
 * Filters an array of log entries to only those that fall within the
 * date range selected by the teacher (mentalStartDate to mentalEndDate).
 * If either date input is empty, that boundary is not applied.
 *
 * @param {object[]} entries - All log entries.
 * @returns {object[]} Filtered subset within the date range.
 */
function getFilteredEntries(entries) {
  // Parse start/end dates; null means "no limit" for that boundary.
  const start = mentalStartDate.value ? new Date(mentalStartDate.value + "T00:00:00").getTime() : null;
  const end   = mentalEndDate.value   ? new Date(mentalEndDate.value   + "T23:59:59").getTime() : null;

  return entries.filter((entry) => {
    const time = parseEntryTimestamp(entry);

    if (start && time < start) {
      return false; // Entry is before the start date.
    }

    if (end && time > end) {
      return false; // Entry is after the end date.
    }

    return true;
  });
}

// ── Rendering ───────────────────────────────────────────────────────────────────────

/**
 * renderEntries()
 * Rebuilds the wellbeing log list from localStorage, applying the current
 * date filter. Shows entries newest-first. Updates the stat counters at the top.
 * Called after every add, clear, filter, or seed action.
 */
function renderEntries() {
  const allEntries = getEntries();
  const entries    = getFilteredEntries(allEntries);
  mentalList.innerHTML = "";

  if (entries.length === 0) {
    mentalList.innerHTML = '<div class="list-item"><p>No entries yet.</p></div>';
  } else {
    entries
      .slice()   // Don't mutate the original array.
      .reverse() // Show newest entries at the top.
      .forEach((entry) => {
        const item = document.createElement("div");
        item.className = "list-item";

        // "High" concern uses an orange pill; everything else uses the default blue pill.
        const concernClass = entry.concernLevel === "High" ? "pill warn" : "pill";
        // "Good" mood uses a green pill; everything else uses the default.
        const moodClass    = entry.moodLevel    === "Good" ? "pill good" : "pill";

        item.innerHTML = `
          <div>
            <p><strong>${entry.studentName}</strong> - ${formatDate(parseEntryTimestamp(entry))}</p>
            <p>Mood: <span class="${moodClass}">${entry.moodLevel}</span></p>
            <p>Concern: <span class="${concernClass}">${entry.concernLevel}</span></p>
            <p>${entry.teacherNote || "No note provided."}</p>
          </div>
        `;

        mentalList.appendChild(item);
      });
  }

  // Update the summary stat counters above the list.
  const highConcern = entries.filter((entry) => entry.concernLevel === "High").length;
  const lowMood     = entries.filter((entry) => entry.moodLevel    === "Low").length;

  totalChecks.textContent     = entries.length;
  highConcernCount.textContent = highConcern;
  lowMoodCount.textContent     = lowMood;
}

// ── Event Listeners ───────────────────────────────────────────────────────────────────

// Add a new wellbeing log entry when the form is submitted.
wellbeingForm.addEventListener("submit", (event) => {
  event.preventDefault(); // Prevent page reload.

  const formData = new FormData(wellbeingForm);
  const entries  = getEntries();
  const now      = Date.now(); // Current time as a Unix timestamp.

  // Push the new entry with both a formatted date string AND a raw timestamp.
  entries.push({
    studentName:  formData.get("studentName").toString().trim(),
    moodLevel:    formData.get("moodLevel").toString(),
    concernLevel: formData.get("concernLevel").toString(),
    teacherNote:  formData.get("teacherNote").toString().trim(),
    date:         new Date(now).toLocaleString(), // Human-readable, for display.
    timestamp:    now                             // Raw ms, for filtering and sorting.
  });

  saveEntries(entries);
  wellbeingForm.reset();
  mentalStatus.textContent = "Wellbeing entry saved successfully.";
  renderEntries(); // Refresh the list immediately.
});

// Clear all entries from localStorage when the Clear button is clicked.
clearMentalLogButton.addEventListener("click", () => {
  localStorage.removeItem(STORAGE_KEY);
  mentalStatus.textContent = "All wellbeing entries were cleared.";
  renderEntries();
});

// Export the currently filtered entries to a CSV file.
exportMentalCsvButton.addEventListener("click", () => {
  const entries = getFilteredEntries(getEntries());

  if (entries.length === 0) {
    mentalStatus.textContent = "No entries available to export.";
    return;
  }

  // Build a 2D array: header row + one data row per entry.
  const rows = [
    ["Student Name", "Mood Level", "Concern Level", "Teacher Note", "Date"],
    ...entries.map((entry) => [
      entry.studentName,
      entry.moodLevel,
      entry.concernLevel,
      entry.teacherNote,
      formatDate(parseEntryTimestamp(entry))
    ])
  ];

  downloadCsv("mental-health-log.csv", rows);
  mentalStatus.textContent = "CSV exported successfully.";
});

// Seed the log with three example entries so the teacher can see how it looks.
// Uses timestamps spaced 1 and 2 days in the past so the filter range
// feature can also be demonstrated. 86400000 ms = 24 hours.
seedMentalDemoButton.addEventListener("click", () => {
  const entries = getEntries();
  const base    = Date.now(); // Current time in milliseconds.

  const samples = [
    {
      studentName: "Aisha",
      moodLevel:   "Good",
      concernLevel: "Low",
      teacherNote: "Participated well in class discussion.",
      timestamp:   base - 86400000 * 2 // 2 days ago.
    },
    {
      studentName: "Bilal",
      moodLevel:   "Low",
      concernLevel: "High",
      teacherNote: "Quiet today. Follow-up conversation needed.",
      timestamp:   base - 86400000     // 1 day ago.
    },
    {
      studentName: "Sara",
      moodLevel:   "Okay",
      concernLevel: "Medium",
      teacherNote: "Improved focus after break.",
      timestamp:   base                // Now.
    }
  ];

  samples.forEach((sample) => {
    entries.push({
      studentName:  sample.studentName,
      moodLevel:    sample.moodLevel,
      concernLevel: sample.concernLevel,
      teacherNote:  sample.teacherNote,
      timestamp:    sample.timestamp,
      date:         formatDate(sample.timestamp)
    });
  });

  saveEntries(entries);
  mentalStatus.textContent = "Demo data added.";
  renderEntries();
});

// Apply the current date filter and re-render the list.
applyMentalFilterButton.addEventListener("click", () => {
  mentalStatus.textContent = "Date filter applied.";
  renderEntries();
});

// Reset the date filter inputs and re-render all entries.
resetMentalFilterButton.addEventListener("click", () => {
  mentalStartDate.value = "";
  mentalEndDate.value   = "";
  mentalStatus.textContent = "Date filter reset.";
  renderEntries();
});

// Trigger the browser's print dialog to print the current log view.
printMentalReportButton.addEventListener("click", () => {
  window.print();
});

// ── Initialisation ────────────────────────────────────────────────────────────
// Render the log immediately when the page loads so saved entries appear right away.
renderEntries();
