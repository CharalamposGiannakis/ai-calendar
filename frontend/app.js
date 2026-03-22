const API_BASE = "http://127.0.0.1:8000";

const selectedDateInput = document.getElementById("selected-date");
const loadEventsBtn = document.getElementById("load-events-btn");
const todayBtn = document.getElementById("today-btn");
const eventsContainer = document.getElementById("events-container");
const eventsSummary = document.getElementById("events-summary");

const eventForm = document.getElementById("event-form");
const clearFormBtn = document.getElementById("clear-form-btn");
const formMessage = document.getElementById("form-message");

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

function getTodayString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function setDefaultDates() {
  const today = getTodayString();
  selectedDateInput.value = today;
  startDateInput.value = today;
  endDateInput.value = today;
  startTimeInput.value = "09:00";
  endTimeInput.value = "10:00";
}

function showFormMessage(message, type = "") {
  formMessage.textContent = message;
  formMessage.className = `message ${type}`.trim();
}

function clearForm() {
  titleInput.value = "";
  descriptionInput.value = "";
  locationInput.value = "";
  allDayInput.checked = false;
  categorySelect.value = "";
  setDefaultDates();
  showFormMessage("");
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

function renderEvents(events, selectedDate) {
  if (!events.length) {
    eventsSummary.textContent = `0 events for ${selectedDate}`;
    eventsContainer.innerHTML = `<p class="empty-state">No events found for this date.</p>`;
    return;
  }

  eventsSummary.textContent = `${events.length} event(s) for ${selectedDate}`;

  eventsContainer.innerHTML = events
    .map((event) => {
      const borderColor = getCategoryColor(event.category_id);
      const categoryName = getCategoryName(event.category_id);

      return `
        <article class="event-card" style="border-left-color: ${borderColor}">
          <h3>${escapeHtml(event.title)}</h3>
          <p class="event-meta"><strong>When:</strong> ${formatDateTime(event.start_datetime)} → ${formatDateTime(event.end_datetime)}</p>
          <p class="event-meta"><strong>Category:</strong> ${escapeHtml(categoryName)}</p>
          <p class="event-meta"><strong>Location:</strong> ${escapeHtml(event.location || "-")}</p>
          <p class="event-meta"><strong>Description:</strong> ${escapeHtml(event.description || "-")}</p>
        </article>
      `;
    })
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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
  renderEvents(data, dateString);
}

function buildEventPayload() {
  const startDateTime = `${startDateInput.value}T${startTimeInput.value}:00`;
  const endDateTime = `${endDateInput.value}T${endTimeInput.value}:00`;

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
    const detail = body?.detail || "Failed to create event.";
    throw new Error(detail);
  }

  return body;
}

loadEventsBtn.addEventListener("click", async () => {
  const dateValue = selectedDateInput.value;
  if (!dateValue) return;

  try {
    await fetchEventsForDate(dateValue);
  } catch (error) {
    eventsSummary.textContent = "";
    eventsContainer.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
});

todayBtn.addEventListener("click", async () => {
  const today = getTodayString();
  selectedDateInput.value = today;

  try {
    await fetchEventsForDate(today);
  } catch (error) {
    eventsSummary.textContent = "";
    eventsContainer.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
});

clearFormBtn.addEventListener("click", () => {
  clearForm();
});

eventForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showFormMessage("");

  try {
    const payload = buildEventPayload();

    if (!payload.title) {
      throw new Error("Title is required.");
    }

    await createEvent(payload);
    showFormMessage("Event saved successfully.", "success");

    selectedDateInput.value = payload.start_datetime.slice(0, 10);
    await fetchEventsForDate(selectedDateInput.value);
    clearForm();
  } catch (error) {
    showFormMessage(error.message, "error");
  }
});

async function init() {
  setDefaultDates();

  try {
    await fetchCategories();
    await fetchEventsForDate(selectedDateInput.value);
  } catch (error) {
    eventsSummary.textContent = "";
    eventsContainer.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
    showFormMessage(error.message, "error");
  }
}

init();