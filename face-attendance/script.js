// =============================================================================
// script.js — Face Recognition Attendance System
// =============================================================================
// This file powers the face-attendance/index.html page.
//
// HOW IT WORKS (overview):
//   1. On page load, face-api.js neural network models are downloaded from a CDN.
//   2. The teacher adds students by submitting a name and photo.
//      face-api.js scans the photo and extracts a 128-number "face descriptor"
//      (a mathematical fingerprint of that face). This is stored in localStorage.
//   3. When the webcam starts, the page scans each video frame every 700ms.
//      For each face found, face-api.js compares it against all stored descriptors.
//      If the match score is below the confidence threshold, the student is recognised
//      and their attendance is marked.
//   4. The teacher can also mark students manually, filter by status, export a CSV,
//      email a report, and use the random student picker (roulette).
//
// KEY LIBRARIES (loaded from CDN in the HTML file):
//   face-api.js  — Face detection and recognition (runs entirely in the browser).
//   EmailJS      — Sends the attendance report email without a backend server.
// =============================================================================

// ── DOM References ────────────────────────────────────────────────────────────
// These variables point to HTML elements so we can read and update them from JS.
// They are all declared at the top so every function below can use them.

const addStudentForm        = document.getElementById("addStudentForm");
const classNameInput        = document.getElementById("classNameInput");
const activeClassHint       = document.getElementById("activeClassHint");
const studentNameInput      = document.getElementById("studentName");
const studentImageInput     = document.getElementById("studentImage");
const knownStudentsList     = document.getElementById("knownStudentsList");   // Grid of saved student cards.
const startCameraButton     = document.getElementById("startCameraButton");
const stopCameraButton      = document.getElementById("stopCameraButton");
const video                 = document.getElementById("video");               // <video> element showing webcam feed.
const overlayCanvas         = document.getElementById("overlayCanvas");       // Transparent <canvas> drawn on top of the video.
const attendanceList        = document.getElementById("attendanceList");      // List of student attendance rows.
const cameraStatus          = document.getElementById("cameraStatus");        // Status/feedback message paragraph.
const todayDate             = document.getElementById("todayDate");           // Displays today's date.
const activeClassLabel      = document.getElementById("activeClassLabel");    // Shows which class is selected.
const exportAttendanceButton= document.getElementById("exportAttendanceButton");
const classStartTimeInput   = document.getElementById("classStartTime");      // Time input for late-arrival threshold.
const attendanceSearch      = document.getElementById("attendanceSearch");    // Search box to filter the attendance list.
const presentCount          = document.getElementById("presentCount");        // Counter showing present students.
const absentCount           = document.getElementById("absentCount");         // Counter showing absent students.
const totalCount            = document.getElementById("totalCount");          // Counter showing total students.
const highContrastToggle    = document.getElementById("highContrastToggle");  // Checkbox for accessibility palette.
const showLandmarksToggle   = document.getElementById("showLandmarksToggle"); // Checkbox to overlay facial key-points.
const webcamTab             = document.getElementById("webcamTab");           // Button in the toolbar (also starts camera).
const fpsValue              = document.getElementById("fpsValue");            // Live FPS counter.
const inferenceValue        = document.getElementById("inferenceValue");      // Milliseconds for each scan.
const framesValue           = document.getElementById("framesValue");         // Total frames processed.
const roulettePickButton    = document.getElementById("roulettePickButton");  // Spins the random student picker.
const randomPickResult      = document.getElementById("randomPickResult");    // Shows the picked student's name.
const randomPickHistory     = document.getElementById("randomPickHistory");   // Shows the last 6 picks as chips.
const absenceEmailSummary   = document.getElementById("absenceEmailSummary"); // Small summary text near the email button.
const sendAbsenceEmailsButton = document.getElementById("sendAbsenceEmailsButton");
const teacherReportEmailInput = document.getElementById("teacherReportEmail"); // Email input for sending the report.

// ── Constants: localStorage Keys & EmailJS Config ─────────────────────────────
// All localStorage keys start with a project prefix to avoid clashing with
// other websites stored in the same browser.

// URL where face-api.js downloads its pre-trained model files.
const MODEL_URL = "https://justadudewhohacks.github.io/face-api.js/models";

// Legacy key from an older version that stored all students in a flat array.
// Kept for backwards compatibility when migrating existing data.
const LEGACY_STUDENTS_STORAGE_KEY    = "teacherFeatureHubFaceStudents_v1";

// Current key: stores students organised by class name (object of arrays).
const CLASSROOMS_STORAGE_KEY         = "teacherFeatureHubFaceClassrooms_v1";

// REST endpoint used to persist the roster in the Flask app's SQLite database.
const FACE_STUDENTS_API_URL          = "/api/face-students";

// Remembers which class was last active so it reloads on the next visit.
const ACTIVE_CLASS_STORAGE_KEY       = "teacherFeatureHubActiveClass_v1";

// Saves the class start time so late-arrival detection persists across visits.
const CLASS_START_TIME_STORAGE_KEY   = "teacherFeatureHubClassStartTime_v1";

// Saves the teacher's email so they don't have to retype it every session.
const TEACHER_REPORT_EMAIL_STORAGE_KEY = "teacherFeatureHubTeacherReportEmail_v1";

// EmailJS credentials — used to send the attendance report without a backend.
// These IDs are tied to a specific EmailJS account and template.
const EMAILJS_SERVICE_ID  = "service_apqz4do";
const EMAILJS_TEMPLATE_ID = "template_ulevkre";
const EMAILJS_PUBLIC_KEY  = "8DkU-XfXxtXOT-D19";

// ── Runtime State (in-memory data) ────────────────────────────────────────────
// These variables hold all the data that changes while the page is running.

// Master list of student objects for the currently active class.
// Each student: { name, className, photoDataUrl, descriptor (Float32Array) }
const students = [];

// All students organised by class name: { "CS-101": [...], "Biology": [...] }
// This allows the teacher to switch between classes without losing data.
const studentsByClass = {};

// Tracks which students have been marked present in this session.
// Using a Set means each name can only appear once (no duplicates).
const attendanceSet = new Set();

// Maps student name → time string (e.g. "09:14:32 AM") when they were marked.
const attendanceTimes = new Map();

// Maps student name → timestamp (milliseconds) when they were marked.
// Used to compare against the class start time for late-arrival detection.
const attendanceMarkedAt = new Map();

// face-api.js FaceMatcher object — built from all stored descriptors.
// Null until students are loaded. The scan loop checks this before running.
let matcher = null;

// The active webcam MediaStream. Null when camera is off.
let stream = null;

// ID returned by setInterval for the face-scan loop. Stored so we can stop it.
let scanIntervalId = null;

// Prevents two scans from running at the same time (face detection is async).
let scanInProgress = false;

// True once all three face-api.js models have finished loading from the CDN.
let modelsLoaded = false;

// Which tab filter is active: "all", "present", "late", or "absent".
let activeFilter = "all";

// Total video frames processed since the camera started.
let frameCounter = 0;

// Fixed detection settings for the face matcher and scan loop.
// These used to be controlled by sliders, but are now kept at the same defaults.
const currentThreshold = 0.5;
const currentMaxDetections = 5;
const minDistanceMargin = 0.03;
const recognitionConfirmationsNeeded = 2;
const recognitionCandidateWindowMs = 2500;
const minEnrollmentFaceSizeRatio = 0.18;
const minScanFaceSizePx = 70;

function getEnrollmentDetectorOptions() {
  return new faceapi.TinyFaceDetectorOptions({
    inputSize: 512,
    scoreThreshold: 0.35
  });
}

function getScanDetectorOptions() {
  return new faceapi.TinyFaceDetectorOptions({
    inputSize: 416,
    scoreThreshold: 0.4
  });
}

// Pool of student names available for the random picker.
// Entries are removed as students are picked; refills when empty.
let randomPool = [];

// History of recently picked names, shown as chips below the result.
let recentPicks = [];

// Tracks what criteria filled the pool ("all" or "present").
let randomPoolMode = "all";

// ID for the roulette spin interval timer; stored so we can cancel it.
let rouletteTimerId = null;

// True while the roulette animation is running (prevents double-clicks).
let rouletteRunning = false;

// True once EmailJS has been successfully initialised with the public key.
let emailJsReady = false;

// Name of the class currently being worked with (e.g. "CS-101").
let activeClassName = "";

// Tracks repeated detections before auto-marking a student as present.
const recognitionCandidates = new Map();

// ── Security Helpers ──────────────────────────────────────────────────────────

/**
 * escapeHtml(value)
 * Converts any special HTML characters in a string into safe HTML entities.
 * This prevents XSS (Cross-Site Scripting) attacks when inserting user-provided
 * text (like student names) directly into innerHTML.
 * Example: escapeHtml('<b>') returns '&lt;b&gt;'
 *
 * @param {*} value - Any value; will be converted to a string first.
 * @returns {string} A safe HTML-encoded string.
 */
function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * encodeStudentName(name)
 * URL-encodes a student name so it can be safely stored in an HTML data attribute.
 * For example, "O'Brien" becomes "O%27Brien" — safe to put in data-student-name.
 * decodeStudentName() reverses this when reading the value back.
 */
function encodeStudentName(name) {
  return encodeURIComponent(name);
}

/**
 * decodeStudentName(name)
 * Reverses URL encoding to get the original student name back from a data attribute.
 * The try/catch handles corrupt data gracefully by returning the raw string.
 */
function decodeStudentName(name) {
  try {
    return decodeURIComponent(name);
  } catch (error) {
    return name; // Return the original if decoding fails.
  }
}

/**
 * sanitizeClassName(value)
 * Trims whitespace from a class name string. Returns an empty string for
 * null/undefined values (the `|| ""` handles those cases).
 * Every class name going into storage passes through this function.
 */
function sanitizeClassName(value) {
  return String(value || "").trim();
}

/**
 * ensureClassRecord(className)
 * Creates an empty student array for a class name if one doesn't exist yet.
 * This pattern is called "lazy initialisation" — we only create the record
 * when it is first needed, not upfront.
 * Returns the (possibly newly created) array for that class.
 */
function ensureClassRecord(className) {
  if (!studentsByClass[className]) {
    studentsByClass[className] = [];
  }

  return studentsByClass[className];
}

/**
 * updateClassLabels()
 * Refreshes the two UI labels that show which class is currently active:
 *   - The heading label in the attendance section.
 *   - The hint text under the Class Name input in the Add Student form.
 */
function updateClassLabels() {
  if (activeClassName) {
    activeClassLabel.textContent = `Class: ${activeClassName}`;
    activeClassHint.textContent = `Working class: ${activeClassName}`;
  } else {
    activeClassLabel.textContent = "Class: Not selected";
    activeClassHint.textContent = "Enter a class name, then add students into that class.";
  }
}

/**
 * syncCurrentClassStudents()
 * Copies the current in-memory `students` array back into `studentsByClass`
 * for the active class. This ensures the class-organised store stays up to
 * date before we switch classes or save to localStorage.
 */
function syncCurrentClassStudents() {
  if (!activeClassName) {
    return; // Nothing to sync if no class is active.
  }

  // Overwrite the stored array with a fresh copy of the current students.
  studentsByClass[activeClassName] = students.map((student) => ({
    name: student.name,
    email: student.email,
    className: student.className,
    photoDataUrl: student.photoDataUrl,
    descriptor: new Float32Array(student.descriptor) // Ensure it's always a typed array.
  }));
}

/**
 * resetClassAttendanceState()
 * Clears all attendance tracking data for the current session.
 * Called whenever the teacher switches to a different class, because
 * attendance records belong to a specific class session.
 */
function resetClassAttendanceState() {
  attendanceSet.clear();
  attendanceTimes.clear();
  attendanceMarkedAt.clear();
  recentPicks = [];
  randomPool = [];
  recognitionCandidates.clear();
}

/**
 * clearStudentsByClassStore()
 * Removes every class record from the in-memory studentsByClass object.
 * This keeps the same object reference but resets its contents in place.
 */
function clearStudentsByClassStore() {
  Object.keys(studentsByClass).forEach((className) => {
    delete studentsByClass[className];
  });
}

/**
 * addRecordToClass(className, record)
 * Validates one saved student record and places it into the matching class bucket.
 */
function addRecordToClass(className, record) {
  if (
    typeof record?.name !== "string" ||
    typeof record?.photoDataUrl !== "string" ||
    !Array.isArray(record?.descriptor)
  ) {
    return;
  }

  const targetClass = sanitizeClassName(record.className) || className;
  ensureClassRecord(targetClass).push({
    name:         record.name,
    email:        typeof record?.email === "string" ? record.email : "",
    className:    targetClass,
    photoDataUrl: record.photoDataUrl,
    descriptor:   new Float32Array(record.descriptor)
  });
}

/**
 * hydrateStudentsByClass(classrooms)
 * Rebuilds the in-memory roster from a class-grouped payload.
 */
function hydrateStudentsByClass(classrooms) {
  clearStudentsByClassStore();

  if (!classrooms || typeof classrooms !== "object" || Array.isArray(classrooms)) {
    console.log("[LOAD] Invalid classrooms data:", classrooms);
    return;
  }

  Object.entries(classrooms).forEach((entry) => {
    const className    = sanitizeClassName(entry[0]);
    const classRecords = entry[1];

    if (!className || !Array.isArray(classRecords)) {
      return;
    }

    console.log(`[LOAD] Loading class "${className}" with ${classRecords.length} student(s)`);
    classRecords.forEach((record) => addRecordToClass(className, record));
  });

  const totalClasses = Object.keys(studentsByClass).length;
  const totalStudents = Object.values(studentsByClass).reduce((sum, arr) => sum + arr.length, 0);
  console.log(`[LOAD] Total loaded: ${totalStudents} students across ${totalClasses} class(es)`, Object.keys(studentsByClass));
}

/**
 * loadStudentsFromCache()
 * Reads the current roster from localStorage as a fallback when the server is
 * unreachable or the browser is offline.
 */
function loadStudentsFromCache() {
  const rawClassrooms = localStorage.getItem(CLASSROOMS_STORAGE_KEY);

  if (rawClassrooms) {
    const parsed = JSON.parse(rawClassrooms);
    hydrateStudentsByClass(parsed);
    return;
  }

  const rawLegacyStudents = localStorage.getItem(LEGACY_STUDENTS_STORAGE_KEY);
  if (rawLegacyStudents) {
    const legacy = JSON.parse(rawLegacyStudents);
    if (Array.isArray(legacy)) {
      legacy.forEach((record) => addRecordToClass("General", record));
    }
  }
}

/**
 * persistStudentsToServer(payload)
 * Sends the full roster to the Flask backend so it is stored in SQLite.
 */
async function persistStudentsToServer(payload) {
  const response = await fetch(`${FACE_STUDENTS_API_URL}/sync`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    credentials: "same-origin",
    body: JSON.stringify({ studentsByClass: payload })
  });

  if (!response.ok) {
    throw new Error(`Server sync failed with status ${response.status}`);
  }
}

// ── Class Management ─────────────────────────────────────────────────────────

/**
 * setActiveClass(className, options)
 * Switches the page to work with a different class.
 * Steps:
 *   1. Saves the current class's students back to studentsByClass.
 *   2. Sets activeClassName to the new class.
 *   3. Loads that class's students into the `students` array.
 *   4. Resets all attendance data (starts fresh for the new class).
 *   5. Rebuilds the face matcher and re-renders all UI sections.
 *
 * @param {string} className - The class name to switch to.
 * @param {object} options   - { persist: bool, announce: bool }
 *                             persist=false: don't save to localStorage.
 *                             announce=false: don't update the status text.
 * @returns {boolean} true if the switch succeeded, false if className was empty.
 */
function setActiveClass(className, options = {}) {
  const normalized = sanitizeClassName(className);

  // An empty class name is not valid — nothing to switch to.
  if (!normalized) {
    return false;
  }

  // Default: persist the choice and show a status message.
  const shouldPersist  = options.persist  !== false;
  const shouldAnnounce = options.announce !== false;

  // Step 1: Save current class students so they aren't lost on switch.
  // Only sync if we're actually switching to a different class (not on init or redundant calls).
  if (activeClassName && activeClassName !== normalized) {
    syncCurrentClassStudents();
  }

  // Step 2: Update the global active class name and the input field.
  activeClassName = normalized;
  classNameInput.value = normalized;

  // Step 3: Load the new class's students into the working `students` array.
  const classStudents = ensureClassRecord(normalized);
  students.length = 0; // Clear the array without losing its reference.
  classStudents.forEach((student) => {
    students.push({
      name: student.name,
      email: student.email,
      className: sanitizeClassName(student.className) || normalized,
      photoDataUrl: student.photoDataUrl,
      descriptor: new Float32Array(student.descriptor)
    });
  });

  // Step 4: Reset attendance so a new session starts clean.
  resetClassAttendanceState();

  // Step 5: Rebuild UI components for the new class.
  updateMatcher();
  refillRandomPool();
  renderStudents();
  renderAttendance();
  renderPickHistory();
  updateClassLabels();

  if (shouldPersist) {
    localStorage.setItem(ACTIVE_CLASS_STORAGE_KEY, normalized);
  }

  if (shouldAnnounce) {
    cameraStatus.textContent = `Switched to class ${normalized}.`;
  }

  return true;
}

// ── Attendance Status Logic ───────────────────────────────────────────────────

/**
 * getClassStartTimestamp()
 * Reads the class start time input and converts it to a Unix timestamp
 * (milliseconds) for today's date. Returns null if no time is set.
 * This timestamp is compared against attendanceMarkedAt to detect late arrivals.
 */
function getClassStartTimestamp() {
  const rawValue = classStartTimeInput.value;

  if (!rawValue) {
    return null; // No start time configured — late detection is disabled.
  }

  // The time input gives us "HH:MM" — split and parse both parts.
  const parts = rawValue.split(":");
  if (parts.length !== 2) {
    return null;
  }

  const hour   = Number(parts[0]);
  const minute = Number(parts[1]);
  if (!Number.isInteger(hour) || !Number.isInteger(minute)) {
    return null;
  }

  // Build a Date object set to today at the given hour and minute.
  const startAt = new Date();
  startAt.setHours(hour, minute, 0, 0); // seconds=0, milliseconds=0
  return startAt.getTime(); // Return as a Unix timestamp.
}

/**
 * getAttendanceStatus(name)
 * Returns the attendance status string for a student:
 *   "absent"  — not in attendanceSet (never marked present).
 *   "late"    — in attendanceSet but marked after the class start time.
 *   "present" — in attendanceSet and on time.
 *
 * @param {string} name - The student's name.
 * @returns {"absent"|"late"|"present"} The attendance status.
 */
function getAttendanceStatus(name) {
  // If the student is not in the set, they have not been marked at all.
  if (!attendanceSet.has(name)) {
    return "absent";
  }

  const classStartTimestamp = getClassStartTimestamp();
  const markedAt = attendanceMarkedAt.get(name);

  // If a class start time is set AND the student was marked after it, they are late.
  if (typeof markedAt === "number" && classStartTimestamp !== null && markedAt > classStartTimestamp) {
    return "late";
  }

  return "present";
}

/**
 * getStatusLabel(status)
 * Capitalises the first letter of a status string for display.
 * e.g. "present" → "Present", "late" → "Late".
 */
function getStatusLabel(status) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

/**
 * loadClassStartTime()
 * Restores the class start time from localStorage when the page first loads,
 * so the teacher doesn't have to re-enter it every session.
 */
function loadClassStartTime() {
  const storedValue = localStorage.getItem(CLASS_START_TIME_STORAGE_KEY);
  if (!storedValue) {
    return;
  }

  classStartTimeInput.value = storedValue;
}

/**
 * saveClassStartTime()
 * Called whenever the class start time input changes.
 * Saves the value to localStorage and re-renders the attendance list so
 * late/present statuses update immediately.
 */
function saveClassStartTime() {
  if (!classStartTimeInput.value) {
    // If the field is cleared, remove the saved value and disable late detection.
    localStorage.removeItem(CLASS_START_TIME_STORAGE_KEY);
    cameraStatus.textContent = "Class start time cleared. Late tagging is now disabled.";
    renderAttendance();
    return;
  }

  localStorage.setItem(CLASS_START_TIME_STORAGE_KEY, classStartTimeInput.value);
  cameraStatus.textContent = "Class start time saved. Students marked after this time will be tagged Late.";
  renderAttendance();
}

// ── Email / Reporting ─────────────────────────────────────────────────────────

/**
 * getAbsenceDateLabel()
 * Returns a human-readable date string for today, used in report headings
 * and email subjects. Example: "14 June 2026".
 */
function getAbsenceDateLabel() {
  return new Date().toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric"
  });
}

/**
 * getAttendanceEmailSubjectText()
 * Builds the email subject line for the attendance report.
 * Example: "Attendance Report - CS-101 - 14 June 2026"
 */
function getAttendanceEmailSubjectText() {
  return `Attendance Report - ${activeClassName || "Unassigned Class"} - ${getAbsenceDateLabel()}`;
}

/**
 * getAttendanceStats()
 * Counts present, late, absent, and total students.
 * Returns an object with those four numbers so other functions can display
 * or include them in the email without recalculating.
 *
 * @returns {{ present: number, late: number, absent: number, total: number }}
 */
function getAttendanceStats() {
  const lateCount          = students.filter((student) => getAttendanceStatus(student.name) === "late").length;
  const presentOrLateCount = attendanceSet.size;                        // Everyone in the set (present + late).
  const presentOnlyCount   = Math.max(presentOrLateCount - lateCount, 0); // Subtract late from the total marked.
  const absentOnlyCount    = Math.max(students.length - presentOrLateCount, 0);

  return {
    present: presentOnlyCount,
    late: lateCount,
    absent: absentOnlyCount,
    total: students.length
  };
}

/**
 * buildAttendanceReportMessage()
 * Builds a plain-text summary of the entire class attendance for the day.
 * This text is sent as the email body and can also be read in the console.
 * Each student appears on one line with their status and time.
 *
 * @returns {string} Multi-line report text.
 */
function buildAttendanceReportMessage() {
  const stats = getAttendanceStats();

  // Create one line per student: "- Alice: Present (09:05:12 AM)"
  const lines = students.map((student) => {
    const status = getStatusLabel(getAttendanceStatus(student.name));
    const time   = attendanceTimes.get(student.name) || "Not marked";
    return `- ${student.name}: ${status} (${time})`;
  });

  // Join the header lines and student lines into one string.
  return [
    `Class: ${activeClassName || "Unassigned Class"}`,
    `Attendance Date: ${getAbsenceDateLabel()}`,
    `Total Students: ${stats.total}`,
    `Present: ${stats.present}`,
    `Late: ${stats.late}`,
    `Absent: ${stats.absent}`,
    "",
    "Student-wise Status:",
    ...lines
  ].join("\n");
}

/**
 * updateAbsenceEmailUi()
 * Refreshes the summary label next to the Send button and enables/disables
 * the button based on whether a valid email is entered and students exist.
 */
function updateAbsenceEmailUi() {
  const stats         = getAttendanceStats();
  const email         = teacherReportEmailInput.value.trim();
  const hasValidEmail = email.length > 0 && teacherReportEmailInput.checkValidity();

  // Update the small summary text next to the Send button.
  absenceEmailSummary.textContent = hasValidEmail
    ? `Class ${activeClassName || "N/A"} | ${email} | Present: ${stats.present}, Late: ${stats.late}, Absent: ${stats.absent}`
    : "Enter teacher email to send attendance report.";

  // Disable the Send button if there are no students or no valid email.
  sendAbsenceEmailsButton.disabled = students.length === 0 || !hasValidEmail;
}

/**
 * loadTeacherReportEmail()
 * Restores the previously saved teacher email from localStorage on page load.
 */
function loadTeacherReportEmail() {
  const storedEmail = localStorage.getItem(TEACHER_REPORT_EMAIL_STORAGE_KEY);
  if (!storedEmail) {
    return;
  }

  teacherReportEmailInput.value = storedEmail;
}

/**
 * saveTeacherReportEmail()
 * Called when the teacher email input loses focus or changes.
 * Saves the email to localStorage so it persists across visits.
 * Clears storage if the field is emptied.
 */
function saveTeacherReportEmail() {
  const email = teacherReportEmailInput.value.trim().toLowerCase();

  if (!email) {
    localStorage.removeItem(TEACHER_REPORT_EMAIL_STORAGE_KEY);
    updateAbsenceEmailUi();
    return;
  }

  localStorage.setItem(TEACHER_REPORT_EMAIL_STORAGE_KEY, email);
  updateAbsenceEmailUi();
}

/**
 * initEmailJs()
 * Initialises the EmailJS library with the project's public key.
 * Called once on page load. If EmailJS hasn't loaded or the placeholder IDs
 * haven't been replaced with real ones, the function exits silently and
 * emailJsReady remains false (blocking the Send button).
 */
function initEmailJs() {
  if (
    typeof window.emailjs === "undefined" ||
    EMAILJS_TEMPLATE_ID  === "YOUR_EMAILJS_TEMPLATE_ID" ||
    EMAILJS_PUBLIC_KEY   === "YOUR_EMAILJS_PUBLIC_KEY"
  ) {
    return; // Library not loaded or placeholder credentials still in place.
  }

  window.emailjs.init(EMAILJS_PUBLIC_KEY);
  emailJsReady = true;
}

/**
 * formatEmailJsError(error)
 * Converts an EmailJS error (which can be a string, an object, or null)
 * into a readable error message string for display to the teacher.
 *
 * @param {*} error - The error thrown by emailjs.send().
 * @returns {string} A human-readable error message.
 */
function formatEmailJsError(error) {
  if (!error) {
    return "Unknown EmailJS error.";
  }

  if (typeof error === "string") {
    return error;
  }

  // EmailJS error objects can have status, text, and/or message properties.
  const parts = [error.status, error.text, error.message]
    .filter((value) => Boolean(value))
    .map((value)   => String(value).trim());

  return parts.length > 0 ? parts.join(" | ") : "Unknown EmailJS error.";
}

/**
 * sendAbsenceEmails()
 * Sends the attendance report to the teacher's email via EmailJS.
 * Steps:
 *   1. Validates that a valid email is entered.
 *   2. Checks that EmailJS is ready.
 *   3. Checks that students exist.
 *   4. Sends the email using the pre-configured service and template.
 *   5. Updates the status message with the result.
 *
 * This is an async function because emailjs.send() returns a Promise.
 * The `await` keyword pauses here until the email is sent (or fails).
 */
async function sendAbsenceEmails() {
  const teacherEmail = teacherReportEmailInput.value.trim().toLowerCase();
  const absenceDate  = getAbsenceDateLabel();
  const classLabel   = activeClassName || "Unassigned Class";
  const subject      = getAttendanceEmailSubjectText();
  const message      = buildAttendanceReportMessage();
  const stats        = getAttendanceStats();

  if (!teacherEmail || !teacherReportEmailInput.checkValidity()) {
    cameraStatus.textContent = "Enter a valid teacher email before sending the attendance report.";
    return;
  }

  if (!emailJsReady) {
    cameraStatus.textContent = "EmailJS is not ready. Check the browser key, template ID, and whether the EmailJS script loaded.";
    return;
  }

  if (students.length === 0) {
    cameraStatus.textContent = "No students available yet. Add students before sending an attendance report.";
    return;
  }

  // Save email in case the teacher closes the page before the send finishes.
  localStorage.setItem(TEACHER_REPORT_EMAIL_STORAGE_KEY, teacherEmail);
  sendAbsenceEmailsButton.disabled = true;
  cameraStatus.textContent = `Sending attendance report to ${teacherEmail}...`;

  try {
    // emailjs.send() sends the template variables to the EmailJS template.
    // Multiple aliases (e.g. to_email and recipient_email) are included
    // to be compatible with different EmailJS template variable names.
    await window.emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, {
      to_name:           "Teacher",
      to_email:          teacherEmail,
      recipient_name:    "Teacher",
      recipient_email:   teacherEmail,
      email:             teacherEmail,
      subject,
      absence_date:      absenceDate,
      attendance_date:   absenceDate,
      class_name:        classLabel,
      className:         classLabel,
      total_count:       stats.total,
      present_count:     stats.present,
      late_count:        stats.late,
      absent_count:      stats.absent,
      message,
      attendance_report: message,
      reply_to:          teacherEmail,
      from_name:         "Teacher Feature Hub"
    });

    cameraStatus.textContent = `Attendance report sent to ${teacherEmail}.`;
  } catch (error) {
    const errorMessage = formatEmailJsError(error);
    cameraStatus.textContent = `Attendance report email failed. EmailJS said: ${errorMessage}`;
  }

  updateAbsenceEmailUi(); // Re-enable the button after the request completes.
}

// ── Random Student Picker ────────────────────────────────────────────────────────

/**
 * getPickerCandidates()
 * Returns the names of all students who are currently present or late.
 * Only marked students are included in the random picker so absent students
 * are not called on.
 *
 * @returns {string[]} Array of student name strings.
 */
function getPickerCandidates() {
  return students
    .filter((student) => attendanceSet.has(student.name))
    .map((student) => student.name);
}

/**
 * refillRandomPool()
 * Resets the random pool with all currently present/late students.
 * Called after switching classes, marking attendance, or when the pool runs out.
 */
function refillRandomPool() {
  randomPool     = getPickerCandidates();
  randomPoolMode = "present"; // Tracks that the pool was filled with present students.
}

/**
 * ensureRandomPoolFresh()
 * Checks if the pool needs to be refilled and does so if necessary.
 * Refills when: the pool was filled with a different mode, or it's empty.
 */
function ensureRandomPoolFresh() {
  const desiredMode = "present";

  if (randomPoolMode !== desiredMode) {
    refillRandomPool();
  }

  // Also refill if the pool ran out (everyone has been picked at least once).
  if (randomPool.length === 0) {
    refillRandomPool();
  }
}

/**
 * renderPickHistory()
 * Shows the last 6 picked student names as small chip elements below
 * the result display. Chips appear newest-first (most recent pick at the left).
 */
function renderPickHistory() {
  randomPickHistory.innerHTML = ""; // Clear old chips.

  if (recentPicks.length === 0) {
    return; // Nothing to show yet.
  }

  // Take the last 6 picks and reverse them so newest is first.
  recentPicks.slice(-6).reverse().forEach((name) => {
    const chip = document.createElement("span");
    chip.className   = "pick-chip";
    chip.textContent = name;
    randomPickHistory.appendChild(chip);
  });
}

/**
 * pickFromPool()
 * Picks one student at random from the current pool.
 * The picked name is removed from the pool so they won't be picked again
 * until the entire pool is exhausted (fair round-robin picking).
 * Triggers a CSS animation ("reveal") to make the result appear with a flash.
 *
 * @returns {string|null} The picked student's name, or null if no pick was made.
 */
function pickFromPool() {
  if (students.length === 0) {
    randomPickResult.textContent = "Add at least one saved student first.";
    return null;
  }

  ensureRandomPoolFresh();

  if (randomPool.length === 0) {
    randomPickResult.textContent = "No present or late students available right now.";
    return null;
  }

  // Pick a random index, remove it from the pool with splice, and record the name.
  const randomIndex = Math.floor(Math.random() * randomPool.length);
  const pickedName  = randomPool.splice(randomIndex, 1)[0];

  // Trigger the CSS reveal animation by removing then immediately re-adding the class.
  // void randomPickResult.offsetWidth forces the browser to re-paint, resetting the animation.
  randomPickResult.classList.remove("reveal");
  void randomPickResult.offsetWidth;
  randomPickResult.classList.add("reveal");
  randomPickResult.textContent = `Selected: ${pickedName}`;

  // Add to history and re-render the history chips.
  recentPicks.push(pickedName);
  renderPickHistory();

  // When the pool is empty, auto-refill for the next cycle.
  if (randomPool.length === 0) {
    cameraStatus.textContent = "Random picker cycle complete. Pool refilled for next round.";
    refillRandomPool();
  }

  return pickedName;
}

/**
 * setPickerButtonsDisabled(disabled)
 * Enables or disables the roulette button to prevent interruption during a spin.
 *
 * @param {boolean} disabled - true to disable, false to enable.
 */
function setPickerButtonsDisabled(disabled) {
  roulettePickButton.disabled = disabled;
}

/**
 * startRoulettePick()
 * Runs a "spin" animation that rapidly cycles through random student names
 * before landing on one final pick. The number of spin steps varies slightly
 * each time (14–21 steps) to make the outcome feel unpredictable.
 * Uses setInterval to update the display every 90ms during the spin.
 */
function startRoulettePick() {
  // Don't allow a second spin while one is already running.
  if (rouletteRunning) {
    return;
  }

  const candidates = getPickerCandidates();

  if (candidates.length === 0) {
    randomPickResult.textContent = "No present or late students available for roulette.";
    return;
  }

  rouletteRunning = true;
  setPickerButtonsDisabled(true);

  // Randomise the number of spin frames (14 to 21 inclusive).
  const spinSteps = 14 + Math.floor(Math.random() * 8);
  let step = 0;

  // Each tick: display a random candidate name, then increment the step counter.
  // When step reaches spinSteps, stop the interval and do the real pick.
  rouletteTimerId = window.setInterval(() => {
    const previewName = candidates[Math.floor(Math.random() * candidates.length)];
    randomPickResult.textContent = `Spinning... ${previewName}`;

    step += 1;
    if (step >= spinSteps) {
      window.clearInterval(rouletteTimerId);
      rouletteTimerId = null;
      pickFromPool();               // Do the real pick and show the final name.
      rouletteRunning = false;
      setPickerButtonsDisabled(false);
    }
  }, 90); // Tick every 90 milliseconds.
}

// ── Storage: Save & Load ─────────────────────────────────────────────────────

/**
 * saveStudentsToStorage()
 * Serialises all classes and their students to localStorage as a JSON string.
 * Float32Array descriptors are converted to regular arrays (Array.from) because
 * JSON.stringify cannot handle typed arrays natively.
 * Calling syncCurrentClassStudents() first ensures the in-memory `students`
 * array is written back to `studentsByClass` before serialisation.
 */
async function saveStudentsToStorage() {
  syncCurrentClassStudents(); // Flush current students to studentsByClass first.

  // Build a plain object suitable for JSON.stringify.
  const payload = Object.entries(studentsByClass).reduce((accumulator, entry) => {
    const className    = entry[0];
    const classStudents = entry[1];

    accumulator[className] = classStudents.map((student) => ({
      name:         student.name,
      email:        student.email,
      className:    sanitizeClassName(student.className) || className,
      photoDataUrl: student.photoDataUrl,
      descriptor:   Array.from(student.descriptor) // Convert Float32Array to plain array for JSON.
    }));

    return accumulator;
  }, {});

  // Debug: Log what's being saved to help diagnose data loss.
  const classCount = Object.keys(payload).length;
  const totalStudents = Object.values(payload).reduce((sum, arr) => sum + arr.length, 0);
  console.log(`[SAVE] Saving ${totalStudents} students across ${classCount} class(es):`, Object.keys(payload));

  localStorage.setItem(CLASSROOMS_STORAGE_KEY, JSON.stringify(payload));

  try {
    await persistStudentsToServer(payload);
  } catch (error) {
    cameraStatus.textContent = "Students saved in this browser, but database sync failed.";
  }
}

/**
 * loadStudentsFromStorage()
 * Reads student data from localStorage, rebuilds the studentsByClass object,
 * and activates the previously selected class (or falls back to the first class).
 *
 * Migration: if the NEW key (CLASSROOMS_STORAGE_KEY) doesn't exist but the
 * old key (LEGACY_STUDENTS_STORAGE_KEY) does, the old data is imported into a
 * default "General" class.
 *
 * Validation: each student record is checked for required fields before being
 * added. Invalid records are silently skipped to prevent crashes.
 */
async function loadStudentsFromStorage() {
  const savedActiveClass = sanitizeClassName(localStorage.getItem(ACTIVE_CLASS_STORAGE_KEY));
  let loadedFromServer = false;

  try {
    const response = await fetch(FACE_STUDENTS_API_URL, {
      credentials: "same-origin"
    });

    if (response.ok) {
      const data = await response.json();
      hydrateStudentsByClass(data?.studentsByClass);
      localStorage.setItem(CLASSROOMS_STORAGE_KEY, JSON.stringify(data.studentsByClass || {}));
      loadedFromServer = true;
    }
  } catch (error) {
    // If the API is unavailable, fall back to the browser cache below.
  }

  if (!loadedFromServer) {
    try {
      loadStudentsFromCache();
    } catch (error) {
      // If JSON is corrupt, inform the teacher instead of crashing silently.
      cameraStatus.textContent = "Saved student data is invalid. Add students again.";
    }
  }

  // Choose which class to open: the last saved class, or the first available, or "General".
  const availableClasses = Object.keys(studentsByClass);
  const preferredClass   =
    savedActiveClass && studentsByClass[savedActiveClass]
      ? savedActiveClass
      : availableClasses[0] || "General";

  // Load the preferred class without persisting or announcing (just restore quietly).
  setActiveClass(preferredClass, { persist: false, announce: false });
}

// ── Face-API.js: Models, Matcher & Rendering ───────────────────────────────────

/**
 * loadModels()
 * Downloads and loads three pre-trained neural network models from the CDN:
 *   - tinyFaceDetector  : Detects faces quickly (a lightweight model).
 *   - faceLandmark68Net : Finds 68 key facial points (eyes, nose, mouth, etc.).
 *   - faceRecognitionNet: Generates the 128-number face descriptor.
 *
 * Promise.all() loads all three models simultaneously rather than one at a time,
 * which is faster since network requests can happen in parallel.
 *
 * This is async because the models are downloaded over the network.
 */
async function loadModels() {
  cameraStatus.textContent = "Loading face recognition models...";

  try {
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
      faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
      faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL)
    ]);

    modelsLoaded = true;
    cameraStatus.textContent = "Models loaded. Add students, then start webcam.";
  } catch (error) {
    cameraStatus.textContent = "Model loading failed. Please check internet and refresh the page.";
  }
}

/**
 * updateMatcher()
 * Rebuilds the face-api.js FaceMatcher from the current students array.
 * Must be called whenever students are added, removed, or the threshold changes.
 * If there are no students, sets matcher to null (disabling recognition in the scan loop).
 *
 * How it works:
 *   1. Each student gets a LabeledFaceDescriptors object: { name, [descriptor] }.
 *   2. FaceMatcher wraps all of them and uses Euclidean distance to find the
 *      closest match when a new face descriptor is submitted during scanning.
 *   3. currentThreshold controls how strict the match must be
 *      (lower = stricter = fewer false positives).
 */
function updateMatcher() {
  if (students.length === 0) {
    matcher = null; // No students to match against.
    return;
  }

  // Wrap each student's 128-number descriptor in a face-api.js labelled container.
  const labeledDescriptors = students.map(
    (student) => new faceapi.LabeledFaceDescriptors(student.name, [student.descriptor])
  );

  // Build the matcher with the labelled descriptors and the current threshold.
  matcher = new faceapi.FaceMatcher(labeledDescriptors, currentThreshold);
}

function getDescriptorDistance(firstDescriptor, secondDescriptor) {
  let sum = 0;

  for (let index = 0; index < firstDescriptor.length; index += 1) {
    const delta = firstDescriptor[index] - secondDescriptor[index];
    sum += delta * delta;
  }

  return Math.sqrt(sum);
}

function findBestStudentMatch(descriptor) {
  if (students.length === 0) {
    return {
      label: "unknown",
      distance: Infinity,
      secondDistance: null,
      ambiguous: false
    };
  }

  const rankedMatches = students
    .map((student) => ({
      name: student.name,
      distance: getDescriptorDistance(descriptor, student.descriptor)
    }))
    .sort((left, right) => left.distance - right.distance);

  const best = rankedMatches[0];
  const second = rankedMatches[1] || null;
  const passesThreshold = best.distance <= currentThreshold;
  const hasClearMargin = !second || (second.distance - best.distance) >= minDistanceMargin;

  if (!passesThreshold || !hasClearMargin) {
    return {
      label: "unknown",
      distance: best.distance,
      secondDistance: second ? second.distance : null,
      ambiguous: passesThreshold && !hasClearMargin
    };
  }

  return {
    label: best.name,
    distance: best.distance,
    secondDistance: second ? second.distance : null,
    ambiguous: false
  };
}

function registerRecognitionCandidate(name, distance) {
  const now = Date.now();
  const existing = recognitionCandidates.get(name);

  if (!existing || (now - existing.lastSeenAt) > recognitionCandidateWindowMs) {
    recognitionCandidates.set(name, {
      count: 1,
      lastSeenAt: now,
      bestDistance: distance
    });
    return false;
  }

  existing.count += 1;
  existing.lastSeenAt = now;
  existing.bestDistance = Math.min(existing.bestDistance, distance);
  recognitionCandidates.set(name, existing);
  return existing.count >= recognitionConfirmationsNeeded;
}

function pruneRecognitionCandidates() {
  const now = Date.now();

  recognitionCandidates.forEach((candidate, name) => {
    if ((now - candidate.lastSeenAt) > recognitionCandidateWindowMs) {
      recognitionCandidates.delete(name);
    }
  });
}

function hasLargeEnoughFace(box, minSize) {
  return box.width >= minSize && box.height >= minSize;
}

/**
 * renderStudents()
 * Rebuilds the saved students grid from the in-memory `students` array.
 * Each card shows the student's photo, name, and class, plus a Delete button.
 * The Delete button uses a data-student-name attribute with the URL-encoded name
 * to safely pass the name through the HTML without XSS risk.
 */
function renderStudents() {
  knownStudentsList.innerHTML = ""; // Clear the grid.

  if (students.length === 0) {
    knownStudentsList.innerHTML = "<p>No students added yet.</p>";
    return;
  }

  students.forEach((student) => {
    const card     = document.createElement("article");
    card.className = "student-card";
    // escapeHtml() prevents student names or emails from being interpreted as HTML.
    card.innerHTML = `
      <img src="${student.photoDataUrl}" alt="${escapeHtml(student.name)}" />
      <div class="student-card-main">
        <div class="student-info">
          <p><strong>${escapeHtml(student.name)}</strong></p>
          <small>${escapeHtml(student.className || activeClassName)}</small>
        </div>
        <button type="button" class="delete-student" data-student-name="${encodeStudentName(student.name)}">
          Delete Student
        </button>
      </div>
    `;
    knownStudentsList.appendChild(card);
  });
}

/**
 * deleteStudentByName(studentName)
 * Removes a student from the in-memory `students` array, clears their
 * attendance records, removes them from the random pool and history,
 * saves the updated list to localStorage, and re-renders all UI panels.
 *
 * @param {string} studentName - The exact name of the student to delete.
 */
async function deleteStudentByName(studentName) {
  // Find the student's index. findIndex returns -1 if not found.
  const index = students.findIndex(
    (student) => student.name.toLowerCase() === studentName.toLowerCase()
  );

  if (index === -1) {
    return; // Student not found — nothing to delete.
  }

  // Remove from the students array.
  students.splice(index, 1);

  // Clean up all their attendance state.
  attendanceSet.delete(studentName);
  attendanceTimes.delete(studentName);
  attendanceMarkedAt.delete(studentName);

  // Remove from the random picker pool and history.
  randomPool  = randomPool.filter((name)  => name !== studentName);
  recentPicks = recentPicks.filter((name) => name !== studentName);

  // Persist the change and rebuild all affected UI.
  await saveStudentsToStorage();
  updateMatcher();
  renderStudents();
  renderAttendance();
  renderPickHistory();
  cameraStatus.textContent = `${studentName} removed from known students.`;
}

// ── Attendance UI: Rendering & Actions ────────────────────────────────────────

/**
 * matchesFilter(status)
 * Returns true if a student's status should be shown under the current
 * active filter tab (All / Present / Late / Absent).
 * Note: the "Present" filter tab intentionally includes late students too.
 *
 * @param {string} status - The student's attendance status string.
 * @returns {boolean} Whether this status should be visible.
 */
function matchesFilter(status) {
  if (activeFilter === "all") {
    return true; // "All" tab shows everyone.
  }

  if (activeFilter === "present") {
    // The Present tab groups present AND late together.
    return status === "present" || status === "late";
  }

  return status === activeFilter; // "late" and "absent" tabs match exactly.
}

/**
 * renderAttendance()
 * Rebuilds the attendance list from the current `students` array and state.
 * Each student gets a row showing their name, status badge, time, and an
 * action button to toggle their status (Mark Present / Mark Absent).
 *
 * Steps:
 *   1. Collect all students and compute their attendance status.
 *   2. Filter by the search query and the active filter tab.
 *   3. Build an <article> element for each matching student.
 *   4. Update the counter numbers (present / absent / total).
 *   5. Refresh the email UI button state.
 */
function renderAttendance() {
  attendanceList.innerHTML = ""; // Clear existing rows.
  updateClassLabels();           // Keep the class label fresh.

  const query = attendanceSearch.value.trim().toLowerCase();

  // Build a data object for each student, then apply the two filters.
  const records = students
    .map((student) => {
      const status = getAttendanceStatus(student.name);
      return {
        name:   student.name,
        email:  student.email,
        status,
        time: attendanceTimes.get(student.name) || "Not marked yet"
      };
    })
    .filter((record) => record.name.toLowerCase().includes(query)) // Search filter.
    .filter((record) => matchesFilter(record.status));              // Tab filter.

  if (records.length === 0) {
    attendanceList.innerHTML = "<p class=\"status-text\">No students in this view.</p>";
  }

  records.forEach((record) => {
    const row       = document.createElement("article");
    row.className   = `student-row ${record.status}`; // CSS class colours the row.
    const encodedName = encodeStudentName(record.name);

    // Build the status description text shown under the student's name.
    const statusText =
      record.status === "absent"
        ? "Not marked present today"
        : record.status === "late"
          ? `Late arrival at ${record.time}`
          : `Marked at ${record.time}`;

    // One action button: "Mark Present" for absent students, "Mark Absent" for the rest.
    const actionButton =
      record.status === "absent"
        ? `<button class="mini-btn present" data-action="mark-present" data-student-name="${encodedName}" type="button">Mark Present</button>`
        : `<button class="mini-btn absent" data-action="mark-absent" data-student-name="${encodedName}" type="button">Mark Absent</button>`;

    // escapeHtml prevents XSS when inserting student names into innerHTML.
    row.innerHTML = `
      <div class="avatar">${escapeHtml(record.name.charAt(0).toUpperCase())}</div>
      <div class="meta">
        <strong>${escapeHtml(record.name)}</strong>
        <p>${statusText}</p>
      </div>
      <div class="row-actions">
        <div class="badge-group">
          <span class="badge ${record.status}">${record.status.toUpperCase()}</span>
        </div>
        ${actionButton}
      </div>
    `;
    attendanceList.appendChild(row);
  });

  // Update the counter values shown above the list.
  presentCount.textContent = attendanceSet.size;
  absentCount.textContent  = Math.max(students.length - attendanceSet.size, 0);
  totalCount.textContent   = students.length;

  // Refresh the email button state (enable/disable based on current counts).
  updateAbsenceEmailUi();
}

/**
 * markStudentPresent(name)
 * Manually marks a student as present by adding them to attendanceSet
 * and recording the current timestamp. Triggers a re-render of the list.
 * If the class start time is set and the current time is past it, the student
 * will automatically show as "late" instead of "present".
 *
 * @param {string} name - The student's name.
 */
function markStudentPresent(name) {
  // Guard: only mark students who are actually registered.
  if (!students.some((student) => student.name === name)) {
    return;
  }

  const markedAt = Date.now(); // Current time in milliseconds.
  attendanceSet.add(name);
  attendanceTimes.set(name, new Date(markedAt).toLocaleTimeString()); // Human-readable time.
  attendanceMarkedAt.set(name, markedAt);                              // Raw timestamp for late detection.
  refillRandomPool(); // Include this student in the random picker now.

  // Determine if they count as late or on time.
  const status = getAttendanceStatus(name);
  cameraStatus.textContent =
    status === "late"
      ? `${name} manually set to late.`
      : `${name} manually set to present.`;
  renderAttendance();
}

/**
 * markStudentAbsent(name)
 * Reverses a previous present/late marking by removing the student from
 * attendanceSet and clearing their time records.
 *
 * @param {string} name - The student's name.
 */
function markStudentAbsent(name) {
  attendanceSet.delete(name);
  attendanceTimes.delete(name);
  attendanceMarkedAt.delete(name);
  refillRandomPool(); // Remove them from the random pool too.
  cameraStatus.textContent = `${name} moved to absent.`;
  renderAttendance();
}

// ── CSV Export ───────────────────────────────────────────────────────────────────

/**
 * csvCell(value)
 * Wraps a value in double quotes for CSV output and escapes any double
 * quotes inside the value by doubling them (standard CSV escaping).
 * Example: csvCell('She said "hi"') returns '"She said ""hi"""'
 *
 * @param {*} value - The cell value to format.
 * @returns {string} A CSV-safe quoted string.
 */
function csvCell(value) {
  return `"${String(value).replace(/"/g, '""')}"`;
}

/**
 * exportAttendanceCsv()
 * Creates a CSV file containing the attendance data for the active class
 * and triggers a browser download. No server is needed — the file is built
 * entirely in memory using a Blob object.
 *
 * Columns: Class, Student Name, Status, Time Marked.
 * The filename is derived from the class name (spaces/special chars replaced with hyphens).
 */
function exportAttendanceCsv() {
  const classForExport = activeClassName || "Unassigned Class";

  // Build a 2D array: first row is the header, remaining rows are one per student.
  const rows = [
    ["Class", "Student", "Status", "Time"],
    ...students.map((student) => [
      classForExport,
      student.name,
      getStatusLabel(getAttendanceStatus(student.name)),
      attendanceTimes.get(student.name) || ""
    ])
  ];

  // Convert to CSV text and create an in-memory file.
  const csvData = rows.map((row) => row.map(csvCell).join(",")).join("\n");
  const blob    = new Blob([csvData], { type: "text/csv;charset=utf-8;" });
  const link    = document.createElement("a");
  link.href     = URL.createObjectURL(blob);

  // Sanitise the class name for use in a filename.
  const safeClassName = classForExport.replace(/[^a-z0-9-_]+/gi, "-").toLowerCase() || "class";
  link.download = `attendance-${safeClassName}.csv`;

  // Programmatically click the link to trigger the download, then free the URL.
  link.click();
  URL.revokeObjectURL(link.href);
}

// ── Image Processing ──────────────────────────────────────────────────────────────────

/**
 * fileToImage(file)
 * Converts a File object (from a file input) into an HTMLImageElement that
 * face-api.js can analyse. Returns a Promise because reading a file and
 * loading an image are both asynchronous operations.
 *
 * How it works:
 *   1. FileReader reads the file as a base64 data URL (text string).
 *   2. Once the file is read, a new <img> element is created and its src is set.
 *   3. When the image finishes loading, the Promise resolves with the <img>.
 *   4. Either failure (bad file or corrupt image) rejects the Promise.
 *
 * @param {File} file - The image file selected by the teacher.
 * @returns {Promise<HTMLImageElement>} Resolves with the loaded image element.
 */
function fileToImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      // Once the file is read, create an Image and set its src to the data URL.
      const img    = new Image();
      img.onload   = () => resolve(img);  // Resolve with the ready image.
      img.onerror  = () => reject(new Error("Could not load the selected image."));
      img.src      = reader.result;       // reader.result is the base64 data URL.
    };

    reader.onerror = () => reject(new Error("Could not read the selected file."));
    reader.readAsDataURL(file); // Start reading the file as a data URL.
  });
}

// ── Event Listeners: Add Student Form ──────────────────────────────────────────

// This is an async event listener because fileToImage() and faceapi detection
// both return Promises. The `await` keyword pauses execution until each
// step completes before moving to the next.
addStudentForm.addEventListener("submit", async (event) => {
  event.preventDefault(); // Stop the form from reloading the page.

  if (!modelsLoaded) {
    cameraStatus.textContent = "Please wait for models to finish loading.";
    return;
  }

  // Read all form values.
  const requestedClassName = sanitizeClassName(classNameInput.value);
  const name               = studentNameInput.value.trim();
  const file               = studentImageInput.files[0];

  if (!requestedClassName || !name || !file) {
    cameraStatus.textContent = "Please provide class name, student name, and photo.";
    return;
  }

  // Switch to the requested class (or create it if new).
  setActiveClass(requestedClassName, { announce: false });

  // Prevent duplicate names within the same class (case-insensitive).
  if (students.some((student) => student.name.toLowerCase() === name.toLowerCase())) {
    cameraStatus.textContent = "This student name already exists. Use a unique name.";
    return;
  }

  cameraStatus.textContent = "Processing student image...";

  try {
    // Step 1: Load the file into an <img> element.
    const image = await fileToImage(file);

    // Step 2: Detect faces and enforce a clean single-face enrollment image.
    const detections = await faceapi
      .detectAllFaces(image, getEnrollmentDetectorOptions())
      .withFaceLandmarks()
      .withFaceDescriptors();

    if (detections.length === 0) {
      cameraStatus.textContent = "No clear face found. Try a brighter, front-facing photo.";
      return;
    }

    if (detections.length > 1) {
      cameraStatus.textContent = "More than one face found. Use a photo with only one student.";
      return;
    }

    const detection = detections[0];
    const minEnrollmentFaceSize = Math.max(
      minScanFaceSizePx,
      Math.min(image.width, image.height) * minEnrollmentFaceSizeRatio
    );

    if (!hasLargeEnoughFace(detection.detection.box, minEnrollmentFaceSize)) {
      cameraStatus.textContent = "Face is too small in the photo. Move closer and try again.";
      return;
    }

    // Step 3: Add the student to the in-memory list.
    students.push({
      name,
      email:        "",                  // Default empty email; can be updated in profile.
      className:    activeClassName,
      photoDataUrl: image.src,           // Store the image as a data URL.
      descriptor:   detection.descriptor // The 128-number face fingerprint.
    });

    // Step 4: Persist, rebuild the matcher, and refresh the UI.
    await saveStudentsToStorage();
    updateMatcher();
    renderStudents();
    refillRandomPool();
    addStudentForm.reset();
    classNameInput.value = activeClassName; // Keep the class name input filled.
    updateClassLabels();
    cameraStatus.textContent = `${name} added to class ${activeClassName}.`;
  } catch (error) {
    cameraStatus.textContent = "Could not process this image. Please try another file.";
  }
});

// Event delegation for the Delete Student buttons inside knownStudentsList.
// Instead of adding a listener to each button individually, we listen on the
// parent and check which button was clicked. This works for dynamically created elements.
knownStudentsList.addEventListener("click", async (event) => {
  const target = event.target;

  // Only handle actual button clicks.
  if (!(target instanceof HTMLButtonElement)) {
    return;
  }

  // Only handle Delete Student buttons (ignore other buttons in the same list).
  if (!target.classList.contains("delete-student")) {
    return;
  }

  // Decode the student name from the data attribute.
  const studentName = decodeStudentName(target.dataset.studentName || "");

  if (!studentName) {
    return;
  }

  await deleteStudentByName(studentName);
});

// ── Webcam: Start & Stop ─────────────────────────────────────────────────────────────

/**
 * startCamera()
 * Requests access to the user's webcam and starts the video feed.
 * The browser will ask the user for camera permission the first time.
 * Once the video starts playing, the scan loop begins automatically via
 * the `video.addEventListener("playing", ...)` listener below.
 *
 * This is async because getUserMedia() returns a Promise.
 */
async function startCamera() {
  if (!modelsLoaded) {
    cameraStatus.textContent = "Models are still loading. Please wait.";
    return;
  }

  if (stream) {
    cameraStatus.textContent = "Webcam is already running.";
    return;
  }

  try {
    // Request the webcam stream from the browser.
    stream          = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream; // Attach the stream to the <video> element.
    cameraStatus.textContent = matcher
      ? "Webcam started. Scanning faces..."
      : "Webcam started. Add students to enable face recognition.";
  } catch (error) {
    cameraStatus.textContent = "Camera access failed. Check browser permission settings.";
  }
}

/**
 * stopCamera()
 * Stops the webcam stream and clears the canvas overlay.
 * Also stops the face-scan interval so it doesn't keep running in the background.
 */
function stopCamera() {
  // Cancel the periodic scan interval.
  if (scanIntervalId) {
    clearInterval(scanIntervalId);
    scanIntervalId = null;
  }

  // Stop each track in the MediaStream (releases the camera hardware).
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  // Clear the video element and the overlay canvas.
  video.srcObject = null;
  const context = overlayCanvas.getContext("2d");
  context.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  recognitionCandidates.clear();
  cameraStatus.textContent = "Webcam stopped.";
  fpsValue.textContent     = "0.0";
}

// ── Webcam Scan Loop (runs on every video frame update) ─────────────────────────

// This event fires when the webcam video starts playing.
// It sets up a repeating interval (setInterval, every 700ms) that scans
// each video frame for faces and tries to match them against known students.
video.addEventListener("playing", () => {
  frameCounter = 0;

  // Match the canvas size to the actual video resolution.
  const displaySize = {
    width:  video.videoWidth  || 640,
    height: video.videoHeight || 480
  };
  faceapi.matchDimensions(overlayCanvas, displaySize);

  // Clear any existing scan interval before starting a fresh one.
  if (scanIntervalId) {
    clearInterval(scanIntervalId);
  }

  // Start the periodic face scan. Runs every 700ms to balance speed and CPU usage.
  scanIntervalId = setInterval(async () => {
    if (!matcher) {
      return; // Skip if no students are loaded yet.
    }

    if (scanInProgress) {
      return; // Skip if the previous scan hasn't finished (prevents queue build-up).
    }

    scanInProgress = true;
    const startedAt = performance.now(); // Record start time for FPS calculation.

    try {
      // Detect all faces in the current video frame, limited to currentMaxDetections.
      const detections = (
        await faceapi
          .detectAllFaces(video, getScanDetectorOptions())
          .withFaceLandmarks()    // Required for the recognition net.
          .withFaceDescriptors()  // Get the 128-number descriptor for each face.
      )
        .filter((detection) => hasLargeEnoughFace(detection.detection.box, minScanFaceSizePx))
        .slice(0, currentMaxDetections);

      // Scale detection coordinates to match the canvas size.
      const resized = faceapi.resizeResults(detections, displaySize);
      const context = overlayCanvas.getContext("2d");
      context.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height); // Clear old boxes.
      pruneRecognitionCandidates();

      resized.forEach((detection) => {
        // Find the closest matching student for this face descriptor.
        const bestMatch = findBestStudentMatch(detection.descriptor);
        const label     = bestMatch.label;

        // If a known student is recognised and not yet marked, mark them present.
        if (label !== "unknown" && !attendanceSet.has(label)) {
          const confirmed = registerRecognitionCandidate(label, bestMatch.distance);
          if (confirmed) {
            const markedAt = Date.now();
            attendanceSet.add(label);
            attendanceTimes.set(label, new Date(markedAt).toLocaleTimeString());
            attendanceMarkedAt.set(label, markedAt);
            recognitionCandidates.delete(label);
            const status = getAttendanceStatus(label);
            cameraStatus.textContent =
              status === "late"
                ? `${label} confirmed and marked late.`
                : `${label} confirmed and marked present.`;
            renderAttendance();
          }
        }

        // Draw a bounding box around the detected face with the matched name.
        const displayLabel =
          bestMatch.label === "unknown" && bestMatch.ambiguous
            ? `uncertain (${bestMatch.distance.toFixed(2)})`
            : `${bestMatch.label} (${bestMatch.distance.toFixed(2)})`;

        const drawBox = new faceapi.draw.DrawBox(detection.detection.box, {
          label: displayLabel
        });
        drawBox.draw(overlayCanvas);

        // Optionally draw 68 facial landmark dots.
        if (showLandmarksToggle.checked) {
          faceapi.draw.drawFaceLandmarks(overlayCanvas, [detection]);
        }
      });

      // Update the performance metrics display.
      const inferenceMs        = performance.now() - startedAt;
      frameCounter            += 1;
      inferenceValue.textContent = inferenceMs.toFixed(1);
      framesValue.textContent    = frameCounter;
      fpsValue.textContent       = (1000 / Math.max(inferenceMs, 1)).toFixed(1); // Estimated FPS.
    } catch (error) {
      cameraStatus.textContent = "Recognition error occurred. Stop and restart webcam.";
    } finally {
      scanInProgress = false; // Always reset the flag, even if an error occurred.
    }
  }, 700); // Scan every 700 milliseconds.
});

// ── Event Listeners: Attendance Actions ────────────────────────────────────────────

// Refilter the attendance list whenever the teacher types in the search box.
attendanceSearch.addEventListener("input", renderAttendance);

// Event delegation for the Mark Present / Mark Absent buttons.
// Both button types use data-action attributes to identify what they do.
attendanceList.addEventListener("click", (event) => {
  const target = event.target;

  if (!(target instanceof HTMLButtonElement)) {
    return;
  }

  const action      = target.dataset.action;
  const studentName = decodeStudentName(target.dataset.studentName || "");

  if (!action || !studentName) {
    return;
  }

  if (action === "mark-absent") {
    markStudentAbsent(studentName);
    return;
  }

  if (action === "mark-present") {
    markStudentPresent(studentName);
  }
});

// Filter tab buttons (All / Present / Late / Absent).
// Clicking a chip updates activeFilter and re-renders the attendance list.
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    activeFilter = chip.dataset.filter;
    // Deactivate all chips, then activate the clicked one.
    document.querySelectorAll(".chip").forEach((item) => item.classList.remove("active"));
    chip.classList.add("active");
    renderAttendance();
  });
});

// ── Event Listeners: Settings Controls ───────────────────────────────────────────

// High contrast toggle: adds/removes a CSS class on <body> for accessibility.
highContrastToggle.addEventListener("change", () => {
  document.body.classList.toggle("high-contrast", highContrastToggle.checked);
});

// Class name input: switches the active class when the field loses focus or Enter is pressed.
classNameInput.addEventListener("change", () => {
  const requestedClassName = sanitizeClassName(classNameInput.value);

  if (!requestedClassName) {
    cameraStatus.textContent = "Enter a class name before managing students.";
    updateClassLabels();
    return;
  }

  setActiveClass(requestedClassName);
});

// Wire up all the remaining button and input event listeners.
exportAttendanceButton.addEventListener("click",    exportAttendanceCsv);
classStartTimeInput.addEventListener("change",      saveClassStartTime);
roulettePickButton.addEventListener("click",        startRoulettePick);
sendAbsenceEmailsButton.addEventListener("click",   sendAbsenceEmails);
teacherReportEmailInput.addEventListener("change",  saveTeacherReportEmail);
teacherReportEmailInput.addEventListener("input",   updateAbsenceEmailUi);

// If present, the toolbar tab button also starts the camera.
if (webcamTab) {
  webcamTab.addEventListener("click", startCamera);
}
startCameraButton.addEventListener("click",  startCamera);
stopCameraButton.addEventListener("click",   stopCamera);

// When the page is about to be closed or refreshed, stop the camera and clear the
// roulette timer to avoid memory leaks and leaving the camera hardware active.
window.addEventListener("beforeunload", () => {
  if (rouletteTimerId) {
    window.clearInterval(rouletteTimerId);
  }

  stopCamera();
});

// ── Page Initialisation (runs once when the script loads) ───────────────────────────
// These statements run in order when the browser finishes loading script.js.
// The order matters: data must be loaded before the UI is built,
// and models must be requested last because they take the longest.

// Display today's full date in the attendance header.
todayDate.textContent = new Date().toLocaleDateString(undefined, {
  weekday: "long",
  year:    "numeric",
  month:   "long",
  day:     "numeric"
});

void (async () => {
  initEmailJs();            // Set up the EmailJS SDK with the public key.
  loadClassStartTime();     // Restore the class start time from localStorage.
  loadTeacherReportEmail(); // Restore the teacher's saved email.
  await loadStudentsFromStorage(); // Load saved students from the server, then cache fallback.
  updateMatcher();          // Build the face matcher from the loaded students.
  refillRandomPool();       // Fill the random picker with present students (empty on load).
  renderStudents();         // Show the saved student cards.
  renderAttendance();       // Show the attendance list.
  renderPickHistory();      // Show any pick history (empty on load).
  loadModels();             // Start downloading the face-api.js neural network models.
})();
