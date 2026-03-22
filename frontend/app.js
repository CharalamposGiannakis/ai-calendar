const API_BASE = "http://127.0.0.1:8000";

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
const locationInput = document.getElementById("location");
const categorySelect = document.getElementById("category");

let categoriesCache = [];
let currentEvents = [];
let editingEventId = null;

function getTodayString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function toLocalDateTimeString(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
}

function setDefaultFormValues() {
  const today = getTodayString();
  startDateInput.value = today;
  endDateInput.value = today;
  startTimeInput.value = "09:00";
  endTimeInput.value = "10:00";
  allDayInput.checked = false;
  applyAllDayState();
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

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getCategoryColor(categoryId) {
  const category = categoriesCache.find((item) => item.id === categoryId);
  return category?.color || "#2563eb";
}

function getCategoryName(categoryId) {
  const category = categoriesCache.find((item) => item.id === categoryId);
  return category?.name || "No category";
}

function parseDateParts(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return { year, month, day };
}

function parseTimeParts(timeString) {
  const [hours, minutes] = timeString.split(":").map(Number);
  return { hours, minutes };
}

function combineLocalDateTime(dateString, timeString) {
  const { year, month, day } = parseDateParts(dateString);
  const { hours, minutes } = parseTimeParts(timeString);
  return new Date(year, month - 1, day, hours, minutes, 0, 0);
}

function setTimeInputFromDate(input, date) {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  input.value = `${hours}:${minutes}`;
}

function syncEndDateWithStartDate() {
  if (!startDateInput.value) return;

  if (!endDateInput.value || endDateInput.value < startDateInput.value) {
    endDateInput.value = startDateInput.value;
  }

  if (allDayInput.checked) {
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
    endDateInput.value = `${newEnd.getFullYear()}-${String(newEnd.getMonth() + 1).padStart(2, "0")}-${String(newEnd.getDate()).padStart(2, "0")}`;
    setTimeInputFromDate(endTimeInput, newEnd);
  }
}

function applyAllDayState() {
  const isAllDay = allDayInput.checked;

  startTimeInput.disabled = isAllDay;
  endTimeInput.disabled = isAllDay;
  endDateInput.disabled = isAllDay;

  if (isAllDay) {
    endDateInput.value = startDateInput.value || getTodayString();
    startTimeInput.value = "00:00";
    endTimeInput.value = "23:59";
  } else {
    if (!startTimeInput.value) startTimeInput.value = "09:00";
    if (!endTimeInput.value) endTimeInput.value = "10:00";
    syncEndDateWithStartDate();
    syncEndTimeIfNeeded();
  }
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

  const start = new Date(eventData.start_datetime);
  const end = new Date(eventData.end_datetime);

  const startDate = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, "0")}-${String(start.getDate()).padStart(2, "0")}`;
  const endDate = `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, "0")}-${String(end.getDate()).padStart(2, "0")}`;

  startDateInput.value = startDate;
  endDateInput.value = endDate;
  startTimeInput.value = `${String(start.getHours()).padStart(2, "0")}:${String(start.getMinutes()).padStart(2, "0")}`;
  endTimeInput.value = `${String(end.getHours()).padStart(2, "0")}:${String(end.getMinutes()).padStart(2, "0")}`;
  allDayInput.checked = Boolean(eventData.all_day);

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
    eventsContainer.innerHTML = `<p class="empty-state">No events found.</p>`;
    return;
  }

  eventsContainer.innerHTML = events
    .map((event) => {
      const borderColor = getCategoryColor(event.category_id);
      const categoryName = getCategoryName(event.category_id);

      return `
        <article class="event-card" style="border-left-color: ${borderColor}">
          <div class="event-toprow">
            <h3>${escapeHtml(event.title)}</h3>
            <div class="event-actions">
              <button type="button" class="small secondary edit-event-btn" data-id="${event.id}">Edit</button>
              <button type="button" class="small danger delete-event-btn" data-id="${event.id}">🗑</button>
            </div>
          </div>
          <p class="event-meta"><strong>When:</strong> ${formatDateTime(event.start_datetime)} → ${formatDateTime(event.end_datetime)}</p>
          <p class="event-meta"><strong>Category:</strong> ${escapeHtml(categoryName)}</p>
          <p class="event-meta"><strong>Location:</strong> ${escapeHtml(event.location || "-")}</p>
          <p class="event-meta"><strong>Description:</strong> ${escapeHtml(event.description || "-")}</p>
        </article>
      `;
    })
    .join("");
}

async function fetchCategories() {
  const response = await fetch(`${API_BASE}/categories/`);
  if (!response.ok) {
    throw new Error("Failed to load categories.");
  }

  const data = await response.json();
  categoriesCache = data;

  categorySelect.innerHTML = `<option value="">No category</option>`;
  data.forEach((category) => {
    const option = document.createElement("option");
    option.value = category.id;
    option.textContent = category.name;
    categorySelect.appendChild(option);
  });
}

async function fetchEventsForDate(dateString) {
  const startFrom = `${dateString}T00:00:00`;
  const endTo = `${dateString}T23:59:59`;

  const url = `${API_BASE}/events/?start_from=${encodeURIComponent(startFrom)}&end_to=${encodeURIComponent(endTo)}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Failed to load events.");
  }

  const data = await response.json();
  renderEvents(data, `${data.length} event(s) for ${dateString}`);
}

async function fetchUpcomingEvents(limit = 10) {
  const startFrom = toLocalDateTimeString(new Date());
  const url = `${API_BASE}/events/?start_from=${encodeURIComponent(startFrom)}&limit=${limit}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Failed to load upcoming events.");
  }

  const data = await response.json();
  renderEvents(data, `Upcoming ${data.length} event(s)`);
}

async function loadCurrentView() {
  const dateValue = selectedDateInput.value;

  if (dateValue) {
    await fetchEventsForDate(dateValue);
  } else {
    await fetchUpcomingEvents(10);
  }
}

function buildEventPayload() {
  let startDateTime;
  let endDateTime;

  if (allDayInput.checked) {
    startDateTime = `${startDateInput.value}T00:00:00`;
    endDateTime = `${startDateInput.value}T23:59:59`;
  } else {
    startDateTime = `${startDateInput.value}T${startTimeInput.value}:00`;
    endDateTime = `${endDateInput.value}T${endTimeInput.value}:00`;
  }

  return {
    title: titleInput.value.trim(),
    description: descriptionInput.value.trim() || null,
    start_datetime: startDateTime,
    end_datetime: endDateTime,
    all_day: allDayInput.checked,
    location: locationInput.value.trim() || null,
    category_id: categorySelect.value ? Number(categorySelect.value) : null,
    source_type: "manual",
    status: "active",
  };
}

async function createEvent(payload) {
  const response = await fetch(`${API_BASE}/events/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body?.detail || "Failed to create event.");
  }

  return body;
}

async function updateEvent(eventId, payload) {
  const response = await fetch(`${API_BASE}/events/${eventId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body?.detail || "Failed to update event.");
  }

  return body;
}

async function deleteEvent(eventId) {
  const response = await fetch(`${API_BASE}/events/${eventId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to delete event.");
  }
}

loadEventsBtn.addEventListener("click", async () => {
  try {
    await loadCurrentView();
  } catch (error) {
    eventsSummary.textContent = "";
    eventsContainer.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
});

todayBtn.addEventListener("click", async () => {
  selectedDateInput.value = getTodayString();

  try {
    await loadCurrentView();
  } catch (error) {
    eventsSummary.textContent = "";
    eventsContainer.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
});

selectedDateInput.addEventListener("change", async () => {
  try {
    await loadCurrentView();
  } catch (error) {
    eventsSummary.textContent = "";
    eventsContainer.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
});

clearFormBtn.addEventListener("click", () => {
  clearForm();
});

allDayInput.addEventListener("change", () => {
  applyAllDayState();
});

startDateInput.addEventListener("change", () => {
  syncEndDateWithStartDate();
  if (allDayInput.checked) {
    endDateInput.value = startDateInput.value;
  }
  syncEndTimeIfNeeded();
});

startTimeInput.addEventListener("change", () => {
  syncEndTimeIfNeeded();
});

endDateInput.addEventListener("change", () => {
  syncEndDateWithStartDate();
  syncEndTimeIfNeeded();
});

endTimeInput.addEventListener("change", () => {
  syncEndTimeIfNeeded();
});

eventsContainer.addEventListener("click", async (event) => {
  const editButton = event.target.closest(".edit-event-btn");
  const deleteButton = event.target.closest(".delete-event-btn");

  if (editButton) {
    const eventId = Number(editButton.dataset.id);
    const eventData = currentEvents.find((item) => item.id === eventId);
    if (eventData) {
      enterEditMode(eventData);
    }
    return;
  }

  if (deleteButton) {
    const eventId = Number(deleteButton.dataset.id);
    const confirmed = window.confirm("Delete the event?");
    if (!confirmed) return;

    try {
      await deleteEvent(eventId);

      if (editingEventId === eventId) {
        clearForm();
      }

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

    if (!payload.title) {
      throw new Error("Title is required.");
    }

    if (!startDateInput.value) {
      throw new Error("Start date is required.");
    }

    if (!allDayInput.checked && (!startTimeInput.value || !endTimeInput.value)) {
      throw new Error("Start and end time are required.");
    }

    if (editingEventId === null) {
      await createEvent(payload);
      showFormMessage("Event saved successfully.", "success");
    } else {
      await updateEvent(editingEventId, payload);
      showFormMessage("Event updated successfully.", "success");
    }

    if (selectedDateInput.value) {
      selectedDateInput.value = payload.start_datetime.slice(0, 10);
    }

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
    eventsSummary.textContent = "";
    eventsContainer.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
    showFormMessage(error.message, "error");
  }
}

init();