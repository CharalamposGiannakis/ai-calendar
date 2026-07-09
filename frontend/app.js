const API_BASE = "";
const DEFAULT_TIMEZONE = "Europe/Amsterdam";

const selectedDateInput = document.getElementById("selected-date");
const loadEventsBtn = document.getElementById("load-events-btn");
const todayBtn = document.getElementById("today-btn");
const eventsContainer = document.getElementById("events-container");
const eventsSummary = document.getElementById("events-summary");

const eventForm = document.getElementById("event-form");
const clearFormBtn = document.getElementById("clear-form-btn");
const formMessage = document.getElementById("form-message");
const submitButton = eventForm.querySelector('button[type="submit"]');

const titleInput = document.getElementById("title");
const descriptionInput = document.getElementById("description");
const startDateInput = document.getElementById("start-date");
const startTimeInput = document.getElementById("start-time");
const endDateInput = document.getElementById("end-date");
const endTimeInput = document.getElementById("end-time");
const allDayInput = document.getElementById("all-day");
const allDayLastDateInput = document.getElementById("all-day-last-date");
const allDayLastDateField = document.getElementById("all-day-last-date-field");
const startTimeField = document.getElementById("start-time-field");
const endDateField = document.getElementById("end-date-field");
const endTimeField = document.getElementById("end-time-field");
const locationInput = document.getElementById("location");
const categorySelect = document.getElementById("category");

const excelFileInput = document.getElementById("excel-file");
const uploadExcelBtn = document.getElementById("upload-excel-btn");
const extractRowsBtn = document.getElementById("extract-rows-btn");
const generateCandidatesBtn = document.getElementById("generate-candidates-btn");
const reloadCandidatesBtn = document.getElementById("reload-candidates-btn");
const importMessage = document.getElementById("import-message");
const importMetadata = document.getElementById("import-metadata");
const candidateSummary = document.getElementById("candidate-summary");
const candidatesContainer = document.getElementById("candidates-container");

let categoriesCache = [];
let currentEvents = [];
let editingEventId = null;
let currentImport = {
  sourceDocument: null,
  importBatch: null,
  candidates: [],
};

function dateStringFromParts({ year, month, day }) {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function getDatePartsInTimezone(date, timezoneName = DEFAULT_TIMEZONE) {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezoneName,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const parts = Object.fromEntries(
    formatter
      .formatToParts(date)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value]),
  );
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
  };
}

function getTodayString() {
  return dateStringFromParts(getDatePartsInTimezone(new Date()));
}

function parseDateString(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return { year, month, day };
}

function addDays(dateString, days) {
  const { year, month, day } = parseDateString(dateString);
  const value = new Date(Date.UTC(year, month - 1, day + days));
  return dateStringFromParts({
    year: value.getUTCFullYear(),
    month: value.getUTCMonth() + 1,
    day: value.getUTCDate(),
  });
}

function combineLocalDateTime(dateString, timeString) {
  const { year, month, day } = parseDateString(dateString);
  const [hours, minutes] = timeString.split(":").map(Number);
  return new Date(year, month - 1, day, hours, minutes, 0, 0);
}

function setTimeInputFromDate(input, date) {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  input.value = `${hours}:${minutes}`;
}

function showFormMessage(message, type = "") {
  formMessage.textContent = message;
  formMessage.className = `message ${type}`.trim();
}

function showImportMessage(message, type = "") {
  importMessage.textContent = message;
  importMessage.className = `message ${type}`.trim();
}

function normalizeErrorDetail(detail) {
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return detail;
}

async function responseJsonOrError(response, fallbackMessage) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(normalizeErrorDetail(body?.detail) || fallbackMessage);
  }
  return body;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function zonedDateTimeParts(value, timezoneName) {
  const instant = new Date(value);
  if (Number.isNaN(instant.getTime())) {
    throw new Error("The event contains an invalid UTC datetime.");
  }

  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezoneName,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
  const parts = Object.fromEntries(
    formatter
      .formatToParts(instant)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value]),
  );
  return {
    date: dateStringFromParts({
      year: Number(parts.year),
      month: Number(parts.month),
      day: Number(parts.day),
    }),
    time: `${parts.hour}:${parts.minute}`,
  };
}

function formatTimedDateTime(value, timezoneName) {
  const instant = new Date(value);
  if (Number.isNaN(instant.getTime())) return value;

  return new Intl.DateTimeFormat([], {
    timeZone: timezoneName,
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(instant);
}

function formatDateOnly(dateString) {
  const { year, month, day } = parseDateString(dateString);
  return new Intl.DateTimeFormat([], {
    timeZone: "UTC",
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

function formatAllDayRange(eventData) {
  const lastDay = addDays(eventData.end_date, -1);
  if (eventData.start_date === lastDay) {
    return `All day: ${formatDateOnly(eventData.start_date)}`;
  }
  return `All day: ${formatDateOnly(eventData.start_date)} to ${formatDateOnly(lastDay)}`;
}

function getCategoryColor(categoryId) {
  const category = categoriesCache.find((item) => item.id === categoryId);
  return category?.color || "#2563eb";
}

function getCategoryName(categoryId) {
  const category = categoriesCache.find((item) => item.id === categoryId);
  return category?.name || "No category";
}

function categoryOptions(selectedId) {
  const selectedValue = selectedId == null ? "" : String(selectedId);
  return [
    `<option value=""${selectedValue === "" ? " selected" : ""}>No category</option>`,
    ...categoriesCache.map((category) => {
      const selected = String(category.id) === selectedValue ? " selected" : "";
      return `<option value="${category.id}"${selected}>${escapeHtml(category.name)}</option>`;
    }),
  ].join("");
}

function syncEndDateWithStartDate() {
  if (!startDateInput.value) return;

  if (allDayInput.checked) {
    if (!allDayLastDateInput.value || allDayLastDateInput.value < startDateInput.value) {
      allDayLastDateInput.value = startDateInput.value;
    }
    return;
  }

  if (!endDateInput.value || endDateInput.value < startDateInput.value) {
    endDateInput.value = startDateInput.value;
  }
}

function syncEndTimeIfNeeded() {
  if (allDayInput.checked) return;
  if (!startDateInput.value || !endDateInput.value || !startTimeInput.value || !endTimeInput.value) return;

  const start = combineLocalDateTime(startDateInput.value, startTimeInput.value);
  const end = combineLocalDateTime(endDateInput.value, endTimeInput.value);
  if (end <= start) {
    const newEnd = new Date(start.getTime() + 60 * 60 * 1000);
    endDateInput.value = dateStringFromParts({
      year: newEnd.getFullYear(),
      month: newEnd.getMonth() + 1,
      day: newEnd.getDate(),
    });
    setTimeInputFromDate(endTimeInput, newEnd);
  }
}

function applyAllDayState() {
  const isAllDay = allDayInput.checked;
  startTimeInput.disabled = isAllDay;
  endTimeInput.disabled = isAllDay;
  endDateInput.disabled = isAllDay;
  startTimeField.hidden = isAllDay;
  endTimeField.hidden = isAllDay;
  endDateField.hidden = isAllDay;
  allDayLastDateField.hidden = !isAllDay;

  if (isAllDay) {
    allDayLastDateInput.value = allDayLastDateInput.value || startDateInput.value || getTodayString();
    syncEndDateWithStartDate();
    return;
  }

  if (!startTimeInput.value) startTimeInput.value = "09:00";
  if (!endTimeInput.value) endTimeInput.value = "10:00";
  syncEndDateWithStartDate();
  syncEndTimeIfNeeded();
}

function setDefaultFormValues() {
  const today = getTodayString();
  startDateInput.value = today;
  endDateInput.value = today;
  allDayLastDateInput.value = today;
  startTimeInput.value = "09:00";
  endTimeInput.value = "10:00";
  allDayInput.checked = false;
  applyAllDayState();
}

function enterCreateMode() {
  editingEventId = null;
  submitButton.textContent = "Save Event";
}

function enterEditMode(eventData) {
  editingEventId = eventData.id;
  submitButton.textContent = "Update Event";
  titleInput.value = eventData.title || "";
  descriptionInput.value = eventData.description || "";
  locationInput.value = eventData.location || "";
  categorySelect.value = eventData.category_id ?? "";
  allDayInput.checked = Boolean(eventData.all_day);

  if (eventData.all_day) {
    startDateInput.value = eventData.start_date;
    allDayLastDateInput.value = addDays(eventData.end_date, -1);
    endDateInput.value = startDateInput.value;
  } else {
    const timezoneName = eventData.timezone_name || DEFAULT_TIMEZONE;
    const start = zonedDateTimeParts(eventData.start_datetime, timezoneName);
    const end = zonedDateTimeParts(eventData.end_datetime, timezoneName);
    startDateInput.value = start.date;
    startTimeInput.value = start.time;
    endDateInput.value = end.date;
    endTimeInput.value = end.time;
    allDayLastDateInput.value = start.date;
  }

  applyAllDayState();
  showFormMessage(`Editing event #${eventData.id}`, "success");
  titleInput.focus();
}

function clearForm() {
  titleInput.value = "";
  descriptionInput.value = "";
  locationInput.value = "";
  categorySelect.value = "";
  setDefaultFormValues();
  showFormMessage("");
  enterCreateMode();
}

function renderEvents(events, summaryText) {
  currentEvents = events;
  eventsSummary.textContent = summaryText;

  if (!events.length) {
    eventsContainer.innerHTML = '<p class="empty-state">No events found.</p>';
    return;
  }

  eventsContainer.innerHTML = events
    .map((eventData) => {
      const borderColor = getCategoryColor(eventData.category_id);
      const categoryName = getCategoryName(eventData.category_id);
      const when = eventData.all_day
        ? formatAllDayRange(eventData)
        : `${formatTimedDateTime(eventData.start_datetime, eventData.timezone_name)} to ${formatTimedDateTime(eventData.end_datetime, eventData.timezone_name)} (${escapeHtml(eventData.timezone_name)})`;

      return `
        <article class="event-card" style="border-left-color: ${borderColor}">
          <div class="event-toprow">
            <h3>${escapeHtml(eventData.title)}</h3>
            <div class="event-actions">
              <button type="button" class="small secondary edit-event-btn" data-id="${eventData.id}">Edit</button>
              <button type="button" class="small danger delete-event-btn" data-id="${eventData.id}">Delete</button>
            </div>
          </div>
          <p class="event-meta"><strong>When:</strong> ${when}</p>
          <p class="event-meta"><strong>Category:</strong> ${escapeHtml(categoryName)}</p>
          <p class="event-meta"><strong>Location:</strong> ${escapeHtml(eventData.location || "-")}</p>
          <p class="event-meta"><strong>Description:</strong> ${escapeHtml(eventData.description || "-")}</p>
        </article>
      `;
    })
    .join("");
}

async function fetchCategories() {
  const response = await fetch(`${API_BASE}/categories/`);
  if (!response.ok) throw new Error("Failed to load categories.");

  const data = await response.json();
  categoriesCache = data;
  categorySelect.innerHTML = '<option value="">No category</option>';
  data.forEach((category) => {
    const option = document.createElement("option");
    option.value = category.id;
    option.textContent = category.name;
    categorySelect.appendChild(option);
  });
}

async function fetchEventsForDate(dateString) {
  const params = new URLSearchParams({
    date_from: dateString,
    date_to: addDays(dateString, 1),
    timezone_name: DEFAULT_TIMEZONE,
  });
  const response = await fetch(`${API_BASE}/events/?${params}`);
  if (!response.ok) throw new Error("Failed to load events.");

  const data = await response.json();
  renderEvents(data, `${data.length} event(s) for ${dateString}`);
}

async function fetchUpcomingEvents(limit = 10) {
  const params = new URLSearchParams({
    start_from: new Date().toISOString(),
    date_from: getTodayString(),
    timezone_name: DEFAULT_TIMEZONE,
    limit: String(limit),
  });
  const response = await fetch(`${API_BASE}/events/?${params}`);
  if (!response.ok) throw new Error("Failed to load events.");

  const data = await response.json();
  renderEvents(data, `Upcoming ${data.length} event(s)`);
}

async function loadCurrentView() {
  if (selectedDateInput.value) {
    await fetchEventsForDate(selectedDateInput.value);
  } else {
    await fetchUpcomingEvents(10);
  }
}

function buildEventPayload() {
  const common = {
    title: titleInput.value.trim(),
    description: descriptionInput.value.trim() || null,
    all_day: allDayInput.checked,
    location: locationInput.value.trim() || null,
    category_id: categorySelect.value ? Number(categorySelect.value) : null,
    source_type: "manual",
    status: "active",
  };

  if (allDayInput.checked) {
    if (!startDateInput.value || !allDayLastDateInput.value) {
      throw new Error("Start date and last day are required.");
    }
    if (allDayLastDateInput.value < startDateInput.value) {
      throw new Error("Last day cannot be before the start date.");
    }
    return {
      ...common,
      start_datetime: null,
      end_datetime: null,
      start_date: startDateInput.value,
      end_date: addDays(allDayLastDateInput.value, 1),
      timezone_name: null,
    };
  }

  if (!startDateInput.value || !endDateInput.value || !startTimeInput.value || !endTimeInput.value) {
    throw new Error("Start and end date and time are required.");
  }
  return {
    ...common,
    start_datetime: `${startDateInput.value}T${startTimeInput.value}:00`,
    end_datetime: `${endDateInput.value}T${endTimeInput.value}:00`,
    start_date: null,
    end_date: null,
    timezone_name: DEFAULT_TIMEZONE,
  };
}

async function saveEvent(payload) {
  const isUpdate = editingEventId !== null;
  const response = await fetch(
    `${API_BASE}/events/${isUpdate ? editingEventId : ""}`,
    {
      method: isUpdate ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body?.detail || "Failed to save event.");
  return body;
}

async function deleteEvent(eventId) {
  const response = await fetch(`${API_BASE}/events/${eventId}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Failed to delete event.");
}

function updateImportButtons() {
  const hasBatch = Boolean(currentImport.importBatch?.id);
  extractRowsBtn.disabled = !hasBatch;
  generateCandidatesBtn.disabled = !hasBatch;
  reloadCandidatesBtn.disabled = !hasBatch;
}

function renderImportMetadata(extraText = "") {
  const source = currentImport.sourceDocument;
  const batch = currentImport.importBatch;
  if (!source || !batch) {
    importMetadata.innerHTML = "";
    candidateSummary.textContent = "";
    updateImportButtons();
    return;
  }

  importMetadata.innerHTML = `
    <dl class="metadata-grid">
      <div>
        <dt>File</dt>
        <dd>${escapeHtml(source.original_filename)}</dd>
      </div>
      <div>
        <dt>Source</dt>
        <dd>#${source.id}</dd>
      </div>
      <div>
        <dt>Batch</dt>
        <dd>#${batch.id}</dd>
      </div>
      <div>
        <dt>Stored</dt>
        <dd>${escapeHtml(source.storage_path)}</dd>
      </div>
      <div>
        <dt>Size</dt>
        <dd>${source.size_bytes} bytes</dd>
      </div>
      <div>
        <dt>Status</dt>
        <dd>${escapeHtml(batch.status || "pending")}</dd>
      </div>
    </dl>
  `;
  candidateSummary.textContent = extraText;
  updateImportButtons();
}

function replaceCandidate(updatedCandidate) {
  currentImport.candidates = currentImport.candidates.map((candidate) =>
    candidate.id === updatedCandidate.id ? updatedCandidate : candidate,
  );
}

function syncImportBatchStatusFromCandidates() {
  if (!currentImport.importBatch || !currentImport.candidates.length) return;
  const pendingCount = currentImport.candidates.filter((candidate) => candidate.review_status === "pending").length;
  currentImport.importBatch.status = pendingCount === 0 ? "completed" : "ready_for_review";
}

function formatCandidateWhen(candidate) {
  if (candidate.all_day) {
    return formatAllDayRange(candidate);
  }
  const timezoneName = candidate.timezone_name || DEFAULT_TIMEZONE;
  return `${formatTimedDateTime(candidate.start_datetime, timezoneName)} to ${formatTimedDateTime(candidate.end_datetime, timezoneName)} (${escapeHtml(timezoneName)})`;
}

function isDateOnlyValue(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""));
}

function formatWarningEventWhen(warning) {
  const start = warning.event_start;
  const end = warning.event_end;
  if (!start || !end) return "";

  if (isDateOnlyValue(start) && isDateOnlyValue(end)) {
    const lastDay = addDays(end, -1);
    if (start === lastDay) {
      return formatDateOnly(start);
    }
    return `${formatDateOnly(start)} to ${formatDateOnly(lastDay)}`;
  }

  if (!isDateOnlyValue(start) && !isDateOnlyValue(end)) {
    return `${formatTimedDateTime(start, DEFAULT_TIMEZONE)} to ${formatTimedDateTime(end, DEFAULT_TIMEZONE)}`;
  }

  return `${start} to ${end}`;
}

function warningHeading(warning) {
  if (warning.type === "duplicate") return "Possible duplicate of";
  if (warning.type === "conflict") return "Conflict with";
  return "Warning for";
}

function renderCandidateWarnings(candidate) {
  const warnings = candidate.warnings || [];
  if (!warnings.length) return "";

  return `
    <div class="candidate-warnings" aria-label="Candidate warnings">
      ${warnings
        .map((warning) => {
          const warningType = warning.type === "duplicate" ? "duplicate" : "conflict";
          const eventTitle = warning.event_title || `Event #${warning.event_id}`;
          const when = formatWarningEventWhen(warning);

          return `
            <div class="candidate-warning warning-${warningType}">
              <div class="warning-toprow">
                <span class="warning-badge">${escapeHtml(warningType)}</span>
                <strong>${escapeHtml(warningHeading(warning))}: ${escapeHtml(eventTitle)}</strong>
              </div>
              ${when ? `<p>${escapeHtml(when)}</p>` : ""}
              ${warning.message ? `<p>${escapeHtml(warning.message)}</p>` : ""}
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function candidateDateTimeFields(candidate) {
  if (candidate.all_day) {
    return {
      startDate: candidate.start_date,
      lastDay: addDays(candidate.end_date, -1),
      startTime: "09:00",
      endDate: candidate.start_date,
      endTime: "10:00",
      timezoneName: DEFAULT_TIMEZONE,
    };
  }

  const timezoneName = candidate.timezone_name || DEFAULT_TIMEZONE;
  const start = zonedDateTimeParts(candidate.start_datetime, timezoneName);
  const end = zonedDateTimeParts(candidate.end_datetime, timezoneName);
  return {
    startDate: start.date,
    lastDay: start.date,
    startTime: start.time,
    endDate: end.date,
    endTime: end.time,
    timezoneName,
  };
}

function renderCandidateCard(candidate) {
  const fields = candidateDateTimeFields(candidate);
  const pending = candidate.review_status === "pending";
  const disabled = pending ? "" : " disabled";
  const timedHidden = candidate.all_day ? " hidden" : "";
  const allDayHidden = candidate.all_day ? "" : " hidden";

  return `
    <article class="candidate-card" data-id="${candidate.id}">
      <div class="candidate-toprow">
        <div>
          <h3>${escapeHtml(candidate.title)}</h3>
          <p class="candidate-status status-${escapeHtml(candidate.review_status)}">${escapeHtml(candidate.review_status)}</p>
        </div>
        <p class="event-meta">Row #${candidate.source_row_index}</p>
      </div>

      ${renderCandidateWarnings(candidate)}

      <p class="event-meta"><strong>When:</strong> ${formatCandidateWhen(candidate)}</p>
      <p class="event-meta"><strong>Category:</strong> ${escapeHtml(getCategoryName(candidate.category_id))}</p>
      <p class="event-meta"><strong>Location:</strong> ${escapeHtml(candidate.location || "-")}</p>
      <p class="event-meta"><strong>Description:</strong> ${escapeHtml(candidate.description || "-")}</p>

      <div class="candidate-edit-grid">
        <div class="field">
          <label>Title</label>
          <input type="text" class="candidate-title" value="${escapeHtml(candidate.title || "")}"${disabled} />
        </div>

        <div class="field">
          <label>Category</label>
          <select class="candidate-category"${disabled}>${categoryOptions(candidate.category_id)}</select>
        </div>

        <div class="field">
          <label>Description</label>
          <textarea class="candidate-description" rows="2"${disabled}>${escapeHtml(candidate.description || "")}</textarea>
        </div>

        <div class="field">
          <label>Location</label>
          <input type="text" class="candidate-location" value="${escapeHtml(candidate.location || "")}"${disabled} />
        </div>
      </div>

      <div class="field checkbox-row">
        <input type="checkbox" class="candidate-all-day" ${candidate.all_day ? "checked" : ""}${disabled} />
        <label>All day</label>
      </div>

      <div class="candidate-time-grid">
        <div class="field">
          <label>Start Date</label>
          <input type="date" class="candidate-start-date" value="${fields.startDate}"${disabled} />
        </div>

        <div class="field candidate-all-day-field"${allDayHidden}>
          <label>Last Day</label>
          <input type="date" class="candidate-last-day" value="${fields.lastDay}"${disabled} />
        </div>

        <div class="field candidate-timed-field"${timedHidden}>
          <label>Start Time</label>
          <input type="time" class="candidate-start-time" value="${fields.startTime}"${disabled} />
        </div>

        <div class="field candidate-timed-field"${timedHidden}>
          <label>End Date</label>
          <input type="date" class="candidate-end-date" value="${fields.endDate}"${disabled} />
        </div>

        <div class="field candidate-timed-field"${timedHidden}>
          <label>End Time</label>
          <input type="time" class="candidate-end-time" value="${fields.endTime}"${disabled} />
        </div>

        <div class="field candidate-timed-field"${timedHidden}>
          <label>Timezone</label>
          <input type="text" class="candidate-timezone" value="${escapeHtml(fields.timezoneName)}"${disabled} />
        </div>
      </div>

      <div class="toolbar">
        <button type="button" class="small save-candidate-btn"${disabled}>Save Changes</button>
        <button type="button" class="small danger reject-candidate-btn"${disabled}>Reject</button>
        <button type="button" class="small approve-candidate-btn"${disabled}>Approve to Event</button>
      </div>
    </article>
  `;
}

function renderCandidates() {
  if (!currentImport.importBatch) {
    candidatesContainer.innerHTML = '<p class="empty-state">No import batch loaded.</p>';
    candidateSummary.textContent = "";
    return;
  }

  if (!currentImport.candidates.length) {
    candidatesContainer.innerHTML = '<p class="empty-state">No candidates found.</p>';
    candidateSummary.textContent = "No candidates found for this batch.";
    return;
  }

  const pendingCount = currentImport.candidates.filter((candidate) => candidate.review_status === "pending").length;
  const approvedCount = currentImport.candidates.filter((candidate) => candidate.review_status === "approved").length;
  const rejectedCount = currentImport.candidates.filter((candidate) => candidate.review_status === "rejected").length;
  candidateSummary.textContent = `${currentImport.candidates.length} candidate(s): ${pendingCount} pending, ${approvedCount} approved, ${rejectedCount} rejected`;
  candidatesContainer.innerHTML = currentImport.candidates.map(renderCandidateCard).join("");
}

function setCandidateShapeVisibility(card) {
  const isAllDay = card.querySelector(".candidate-all-day").checked;
  card.querySelectorAll(".candidate-timed-field").forEach((field) => {
    field.hidden = isAllDay;
  });
  card.querySelectorAll(".candidate-all-day-field").forEach((field) => {
    field.hidden = !isAllDay;
  });
}

function buildCandidatePayload(card) {
  const isAllDay = card.querySelector(".candidate-all-day").checked;
  const title = card.querySelector(".candidate-title").value.trim();
  if (!title) throw new Error("Candidate title is required.");

  const common = {
    title,
    description: card.querySelector(".candidate-description").value.trim() || null,
    location: card.querySelector(".candidate-location").value.trim() || null,
    category_id: card.querySelector(".candidate-category").value ? Number(card.querySelector(".candidate-category").value) : null,
    all_day: isAllDay,
  };

  const startDate = card.querySelector(".candidate-start-date").value;
  if (!startDate) throw new Error("Start date is required.");

  if (isAllDay) {
    const lastDay = card.querySelector(".candidate-last-day").value;
    if (!lastDay) throw new Error("Last day is required.");
    if (lastDay < startDate) throw new Error("Last day cannot be before the start date.");
    return {
      ...common,
      start_date: startDate,
      end_date: addDays(lastDay, 1),
      start_datetime: null,
      end_datetime: null,
      timezone_name: null,
    };
  }

  const startTime = card.querySelector(".candidate-start-time").value;
  const endDate = card.querySelector(".candidate-end-date").value;
  const endTime = card.querySelector(".candidate-end-time").value;
  const timezoneName = card.querySelector(".candidate-timezone").value.trim() || DEFAULT_TIMEZONE;
  if (!startTime || !endDate || !endTime) {
    throw new Error("Start and end date and time are required.");
  }

  return {
    ...common,
    start_datetime: `${startDate}T${startTime}:00`,
    end_datetime: `${endDate}T${endTime}:00`,
    start_date: null,
    end_date: null,
    timezone_name: timezoneName,
  };
}

function setApprovedEventViewDate(eventData) {
  if (eventData.all_day) {
    selectedDateInput.value = eventData.start_date;
    return;
  }
  const timezoneName = eventData.timezone_name || DEFAULT_TIMEZONE;
  selectedDateInput.value = zonedDateTimeParts(eventData.start_datetime, timezoneName).date;
}

async function uploadExcelFile() {
  const file = excelFileInput.files[0];
  if (!file) throw new Error("Select an .xlsx file first.");
  if (!file.name.toLowerCase().endsWith(".xlsx")) {
    throw new Error("Only .xlsx files are supported.");
  }

  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/imports/excel/upload`, {
    method: "POST",
    body: formData,
  });
  const body = await responseJsonOrError(response, "Failed to upload Excel file.");
  currentImport = {
    sourceDocument: body.source_document,
    importBatch: body.import_batch,
    candidates: [],
  };
  renderImportMetadata("Upload complete. Extract rows next.");
  renderCandidates();
}

async function extractRowsForCurrentBatch() {
  if (!currentImport.importBatch) throw new Error("Upload an Excel file first.");
  const batchId = currentImport.importBatch.id;
  const response = await fetch(`${API_BASE}/imports/excel/batches/${batchId}/extract-rows`, {
    method: "POST",
  });
  const body = await responseJsonOrError(response, "Failed to extract rows.");
  currentImport.importBatch.status = "processing";
  currentImport.importBatch.total_rows_detected = body.rows_extracted;
  renderImportMetadata(`Extracted ${body.rows_extracted} row(s) from ${body.worksheet_name}. Generate candidates next.`);
}

async function generateCandidatesForCurrentBatch() {
  if (!currentImport.importBatch) throw new Error("Upload an Excel file first.");
  const batchId = currentImport.importBatch.id;
  const response = await fetch(`${API_BASE}/imports/excel/batches/${batchId}/generate-candidates`, {
    method: "POST",
  });
  const body = await responseJsonOrError(response, "Failed to generate candidates.");
  currentImport.importBatch.status = "ready_for_review";
  currentImport.importBatch.total_candidate_events = body.candidates_created;
  await loadCandidatesForCurrentBatch();
  renderImportMetadata(`Generated ${body.candidates_created} candidate(s); ${body.rows_failed} row(s) failed.`);
}

async function loadCandidatesForCurrentBatch() {
  if (!currentImport.importBatch) throw new Error("Upload an Excel file first.");
  const batchId = currentImport.importBatch.id;
  const response = await fetch(`${API_BASE}/imports/batches/${batchId}/candidates`);
  const body = await responseJsonOrError(response, "Failed to load candidates.");
  currentImport.candidates = body;
  renderCandidates();
}

async function fetchCandidate(candidateId) {
  const response = await fetch(`${API_BASE}/imports/candidates/${candidateId}`);
  return responseJsonOrError(response, "Failed to refresh candidate warnings.");
}

async function saveCandidate(candidateId, payload) {
  const response = await fetch(`${API_BASE}/imports/candidates/${candidateId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return responseJsonOrError(response, "Failed to save candidate.");
}

async function rejectCandidate(candidateId) {
  const response = await fetch(`${API_BASE}/imports/candidates/${candidateId}/reject`, {
    method: "POST",
  });
  return responseJsonOrError(response, "Failed to reject candidate.");
}

async function approveCandidate(candidateId) {
  const response = await fetch(`${API_BASE}/imports/candidates/${candidateId}/approve`, {
    method: "POST",
  });
  return responseJsonOrError(response, "Failed to approve candidate.");
}

function renderLoadError(error) {
  eventsSummary.textContent = "";
  eventsContainer.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
}

loadEventsBtn.addEventListener("click", async () => {
  try {
    await loadCurrentView();
  } catch (error) {
    renderLoadError(error);
  }
});

todayBtn.addEventListener("click", async () => {
  selectedDateInput.value = getTodayString();
  try {
    await loadCurrentView();
  } catch (error) {
    renderLoadError(error);
  }
});

selectedDateInput.addEventListener("change", async () => {
  try {
    await loadCurrentView();
  } catch (error) {
    renderLoadError(error);
  }
});

clearFormBtn.addEventListener("click", clearForm);
allDayInput.addEventListener("change", applyAllDayState);
startDateInput.addEventListener("change", () => {
  syncEndDateWithStartDate();
  syncEndTimeIfNeeded();
});
allDayLastDateInput.addEventListener("change", syncEndDateWithStartDate);
startTimeInput.addEventListener("change", syncEndTimeIfNeeded);
endDateInput.addEventListener("change", () => {
  syncEndDateWithStartDate();
  syncEndTimeIfNeeded();
});
endTimeInput.addEventListener("change", syncEndTimeIfNeeded);

eventsContainer.addEventListener("click", async (event) => {
  const editButton = event.target.closest(".edit-event-btn");
  const deleteButton = event.target.closest(".delete-event-btn");

  if (editButton) {
    const eventId = Number(editButton.dataset.id);
    const eventData = currentEvents.find((item) => item.id === eventId);
    if (eventData) enterEditMode(eventData);
    return;
  }

  if (deleteButton) {
    const eventId = Number(deleteButton.dataset.id);
    if (!window.confirm("Delete the event?")) return;

    try {
      await deleteEvent(eventId);
      if (editingEventId === eventId) clearForm();
      await loadCurrentView();
      showFormMessage("Event deleted successfully.", "success");
    } catch (error) {
      showFormMessage(error.message, "error");
    }
  }
});

uploadExcelBtn.addEventListener("click", async () => {
  showImportMessage("");
  try {
    await uploadExcelFile();
    showImportMessage("Excel file uploaded.", "success");
  } catch (error) {
    showImportMessage(error.message, "error");
  }
});

extractRowsBtn.addEventListener("click", async () => {
  showImportMessage("");
  try {
    await extractRowsForCurrentBatch();
    showImportMessage("Rows extracted.", "success");
  } catch (error) {
    showImportMessage(error.message, "error");
  }
});

generateCandidatesBtn.addEventListener("click", async () => {
  showImportMessage("");
  try {
    await generateCandidatesForCurrentBatch();
    showImportMessage("Candidates generated.", "success");
  } catch (error) {
    showImportMessage(error.message, "error");
  }
});

reloadCandidatesBtn.addEventListener("click", async () => {
  showImportMessage("");
  try {
    await loadCandidatesForCurrentBatch();
    showImportMessage(
      currentImport.candidates.length ? "Candidates loaded." : "No candidates found.",
      currentImport.candidates.length ? "success" : "error",
    );
  } catch (error) {
    showImportMessage(error.message, "error");
  }
});

candidatesContainer.addEventListener("change", (event) => {
  const allDayToggle = event.target.closest(".candidate-all-day");
  if (!allDayToggle) return;
  const card = allDayToggle.closest(".candidate-card");
  setCandidateShapeVisibility(card);
});

candidatesContainer.addEventListener("click", async (event) => {
  const card = event.target.closest(".candidate-card");
  if (!card) return;

  const candidateId = Number(card.dataset.id);
  const saveButton = event.target.closest(".save-candidate-btn");
  const rejectButton = event.target.closest(".reject-candidate-btn");
  const approveButton = event.target.closest(".approve-candidate-btn");

  try {
    if (saveButton) {
      const payload = buildCandidatePayload(card);
      await saveCandidate(candidateId, payload);
      const updatedCandidate = await fetchCandidate(candidateId);
      replaceCandidate(updatedCandidate);
      renderCandidates();
      showImportMessage("Candidate saved.", "success");
      return;
    }

    if (rejectButton) {
      if (!window.confirm("Reject this candidate?")) return;
      await rejectCandidate(candidateId);
      const updatedCandidate = await fetchCandidate(candidateId);
      replaceCandidate(updatedCandidate);
      syncImportBatchStatusFromCandidates();
      renderImportMetadata();
      renderCandidates();
      showImportMessage("Candidate rejected.", "success");
      return;
    }

    if (approveButton) {
      const result = await approveCandidate(candidateId);
      const updatedCandidate = await fetchCandidate(candidateId);
      replaceCandidate(updatedCandidate);
      syncImportBatchStatusFromCandidates();
      renderImportMetadata();
      setApprovedEventViewDate(result.event);
      await loadCurrentView();
      renderCandidates();
      showImportMessage("Candidate approved and added as a real calendar event.", "success");
    }
  } catch (error) {
    showImportMessage(error.message, "error");
  }
});

eventForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showFormMessage("");

  try {
    const payload = buildEventPayload();
    if (!payload.title) throw new Error("Title is required.");

    await saveEvent(payload);
    showFormMessage(
      editingEventId === null ? "Event saved successfully." : "Event updated successfully.",
      "success",
    );
    if (selectedDateInput.value) selectedDateInput.value = payload.start_date || payload.start_datetime.slice(0, 10);
    await loadCurrentView();
    clearForm();
  } catch (error) {
    showFormMessage(error.message, "error");
  }
});

async function init() {
  selectedDateInput.value = "";
  setDefaultFormValues();
  updateImportButtons();

  try {
    await fetchCategories();
    await loadCurrentView();
  } catch (error) {
    renderLoadError(error);
    showFormMessage(error.message, "error");
  }
}

init();
