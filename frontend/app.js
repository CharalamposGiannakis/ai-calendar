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

let categoriesCache = [];
let currentEvents = [];
let editingEventId = null;

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

  try {
    await fetchCategories();
    await loadCurrentView();
  } catch (error) {
    renderLoadError(error);
    showFormMessage(error.message, "error");
  }
}

init();
