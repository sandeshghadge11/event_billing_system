import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  CalendarDays,
  FileText,
  Gauge,
  IndianRupee,
  LibraryBig,
  Landmark,
  ListChecks,
  Mail,
  Plus,
  ReceiptText,
  Search,
  Settings,
  Sparkles,
  Trash2,
  Users,
  X
} from "lucide-react";
import { bookings as initialBookings, inventoryItems as initialItems, payments as initialPayments } from "./data/sampleData";
import "./styles/app.css";

// Backend API root. All apiRequest() calls append their endpoint path to this.
const API_BASE_URL = "http://127.0.0.1:8000/api";

// Sidebar/page configuration. Each item maps a page id to a label and icon.
const navItems = [
  { id: "dashboard", label: "Dashboard", icon: Gauge },
  { id: "bookings", label: "Bookings", icon: CalendarDays },
  { id: "invoice", label: "Invoice Preview", icon: ReceiptText },
  { id: "events", label: "Events", icon: ListChecks },
  { id: "items", label: "Material Master", icon: LibraryBig },
  { id: "settings", label: "Settings", icon: Settings }
];

// Format rupee values consistently across dashboard, booking detail, and invoice.
function formatCurrency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(value);
}

// Convert backend YYYY-MM-DD dates into readable Indian display dates.
function formatDate(value) {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "long",
    year: "numeric"
  }).format(date);
}

// Generate the next booking number from the current frontend list.
function nextBookingNo(bookings) {
  const maxBookingNo = Math.max(1000, ...bookings.map((booking) => Number(booking.bookingNo) || 1000));
  return String(maxBookingNo + 1);
}

// Date input fields need YYYY-MM-DD, while display dates use formatDate().
function todayInputDate() {
  return new Date().toISOString().slice(0, 10);
}

// Treat spaces-only input as empty before saving.
function isBlank(value) {
  return !String(value ?? "").trim();
}

function mobileDigits(value) {
  return String(value ?? "").replace(/\D/g, "").slice(0, 10);
}

function showRequiredMessage(fieldName) {
  alert(`Please add ${fieldName}.`);
}

function showSaveError(action, error) {
  alert(`${action}: ${error.message}`);
}

function normalizeName(value) {
  const cleanValue = String(value ?? "").trim().replace(/\s+/g, " ");
  if (!cleanValue) return cleanValue;
  return cleanValue[0].toUpperCase() + cleanValue.slice(1);
}

// Convert backend item fields from snake_case/API names into frontend names.
function mapItemFromApi(item) {
  return {
    id: item.id,
    name: item.name,
    category: item.category,
    unit: item.unit,
    rate: Number(item.default_rate),
    status: item.status
  };
}

// Convert backend event type/master rows into the Events page shape.
function mapEventTypeFromApi(eventType) {
  return {
    id: eventType.id,
    name: eventType.name,
    status: eventType.status
  };
}

function mapCompanySettingsFromApi(settings) {
  return {
    companyName: settings.company_name,
    invoicePrefix: settings.invoice_prefix,
    ownerMobile: settings.owner_mobile,
    defaultAdvance: String(Number(settings.default_advance)),
    sendMail: settings.send_mail,
    recvMail: settings.recv_mail
  };
}

function mapCompanySettingsToApi(settings) {
  return {
    company_name: settings.companyName,
    invoice_prefix: settings.invoicePrefix,
    owner_mobile: settings.ownerMobile,
    default_advance: Number(settings.defaultAdvance) || 0,
    send_mail: settings.sendMail,
    recv_mail: settings.recvMail
  };
}

// Convert the nested BookingRead API response into the UI shape used below.
function mapBookingFromApi(booking) {
  return {
    id: booking.id,
    bookingNo: booking.booking_no,
    title: booking.title,
    status: booking.status,
    startDate: formatDate(booking.start_date),
    endDate: formatDate(booking.end_date),
    client: {
      id: booking.client.id,
      name: booking.client.name,
      mobile: booking.client.mobile,
      address: booking.client.address ?? ""
    },
    events: booking.events.map((event) => ({
      id: event.id,
      name: event.name,
      date: formatDate(event.event_date),
      venue: event.venue ?? "",
      lines: event.line_items.map((line) => ({
        id: line.id,
        material: line.material_name,
        quantity: Number(line.quantity),
        rate: Number(line.rate)
      }))
    })),
    payments: booking.payments.map((payment) => ({
      id: payment.id,
      bookingId: booking.id,
      amount: Number(payment.amount),
      mode: payment.mode,
      date: formatDate(payment.payment_date)
    }))
  };
}

// Shared fetch wrapper. Components call this instead of using fetch directly.
async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    // Bubble backend validation/conflict details up to the calling handler.
    const message = await response.text();
    let detail = message;
    try {
      const parsedMessage = JSON.parse(message);
      detail = parsedMessage.detail ?? message;
    } catch (error) {
      detail = message;
    }
    throw new Error(detail || `API request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

// Convert a balance amount into the payment status text shown as "Status".
function paymentStatusFromBalance(balance) {
  return balance > 0 ? "Pending" : "Done";
}

// Calculate subtotal, paid amount, and balance from booking events/payments.
function bookingTotals(booking, paymentList = initialPayments) {
  if (!booking) {
    return {
      subtotal: 0,
      paid: 0,
      balance: 0
    };
  }

  const subtotal = booking.events.reduce(
    (sum, event) =>
      sum +
      event.lines.reduce((eventSum, line) => eventSum + line.quantity * line.rate, 0),
    0
  );
  const paid = paymentList
    .filter((payment) => payment.bookingId === booking.id)
    .reduce((sum, payment) => sum + payment.amount, 0);

  return {
    subtotal,
    paid,
    balance: subtotal - paid
  };
}

function filterBookings(bookings, query) {
  const searchText = query.trim().toLowerCase();
  if (!searchText) return bookings;

  return bookings.filter((booking) => {
    const clientName = booking.client.name.toLowerCase();
    const mobile = booking.client.mobile.toLowerCase();
    return clientName.includes(searchText) || mobile.includes(searchText);
  });
}

function App() {
  // activePage controls which screen is rendered inside the main content area.
  const [activePage, setActivePage] = useState("dashboard");
  // These lists start with local sample data, then refresh from the backend.
  const [bookingList, setBookingList] = useState(initialBookings);
  const [itemList, setItemList] = useState(initialItems);
  const [paymentList, setPaymentList] = useState(initialPayments);
  const [eventTypeList, setEventTypeList] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [companySettings, setCompanySettings] = useState({
    companyName: "Prasad FX Lights",
    invoicePrefix: "PFX",
    ownerMobile: "+91 98765 43210",
    defaultAdvance: "0",
    sendMail: "sandeshghadge301@gmail.com",
    recvMail: "sandeshghadge301@gmail.com"
  });
  // selectedBookingId drives the booking detail and invoice preview screens.
  const [selectedBookingId, setSelectedBookingId] = useState(initialBookings[0].id);
  // modal stores which dialog is open and any context it needs, such as eventId.
  const [modal, setModal] = useState(null);
  const [apiStatus, setApiStatus] = useState("Connecting to backend...");
  const [isSaving, setIsSaving] = useState(false);
  const filteredBookings = useMemo(
    () => filterBookings(bookingList, searchQuery),
    [bookingList, searchQuery]
  );
  // Memoized so the selected booking is recomputed only when the list/id changes.
  const selectedBooking = useMemo(
    () => {
      const sourceBookings = searchQuery.trim() ? filteredBookings : bookingList;
      return sourceBookings.find((booking) => booking.id === selectedBookingId) ?? sourceBookings[0] ?? null;
    },
    [bookingList, filteredBookings, searchQuery, selectedBookingId]
  );

  useEffect(() => {
    // On first load, replace sample data with real database data if available.
    refreshData();
  }, []);

  async function refreshData(preferredBookingId = selectedBookingId) {
    try {
      // Bookings and material master are independent, so load them in parallel.
      const [apiBookings, apiItems, apiEventTypes] = await Promise.all([
        apiRequest("/bookings"),
        apiRequest("/items"),
        apiRequest("/event-types")
      ]);
      const mappedBookings = apiBookings.map(mapBookingFromApi);
      // Payments are nested under bookings in the API, but the UI keeps a flat
      // payment list so bookingTotals() can reuse it everywhere.
      const mappedPayments = mappedBookings.flatMap((booking) => booking.payments);

      setBookingList(mappedBookings);
      setItemList(apiItems.map(mapItemFromApi));
      setEventTypeList(apiEventTypes.map(mapEventTypeFromApi));
      setPaymentList(mappedPayments);
      setSelectedBookingId(
        mappedBookings.some((booking) => booking.id === preferredBookingId)
          ? preferredBookingId
          : mappedBookings[0]?.id
      );
      setApiStatus("Connected to MySQL");
    } catch (error) {
      // If the backend is not running, keep the app usable with sample data.
      setApiStatus("Backend offline, showing local sample data");
      setEventTypeList([]);
    }
  }

  useEffect(() => {
    loadCompanySettings();
  }, []);

  async function loadCompanySettings() {
    try {
      const apiSettings = await apiRequest("/company-settings");
      setCompanySettings(mapCompanySettingsFromApi(apiSettings));
    } catch (error) {
      showSaveError("Could not load company settings", error);
    }
  }

  async function addBooking(payload) {
    if (isBlank(payload.title)) {
      showRequiredMessage("booking name");
      return;
    }
    if (isBlank(payload.clientName)) {
      showRequiredMessage("client name");
      return;
    }
    if (isBlank(payload.mobile)) {
      showRequiredMessage("mobile number");
      return;
    }
    if (!/^\d{10}$/.test(payload.mobile)) {
      alert("Mobile number must be exactly 10 digits.");
      return;
    }

    setIsSaving(true);
    try {
      // Booking creation is two API calls: first create the client, then use the
      // returned client.id to create the booking record.
      const client = await apiRequest("/clients", {
        method: "POST",
        body: JSON.stringify({
          name: payload.clientName.trim(),
          mobile: payload.mobile,
          address: isBlank(payload.address) ? null : payload.address.trim()
        })
      });
      const booking = await apiRequest("/bookings", {
        method: "POST",
        body: JSON.stringify({
          booking_no: nextBookingNo(bookingList),
          title: payload.title.trim(),
          client_id: client.id,
          start_date: payload.startDate || null,
          end_date: payload.endDate || null,
          status: "Pending",
          events: []
        })
      });

      const advanceAmount = Number(payload.advance) || 0;
      if (advanceAmount > 0) {
        await apiRequest(`/bookings/${booking.id}/payments`, {
          method: "POST",
          body: JSON.stringify({
            amount: advanceAmount,
            payment_date: payload.startDate || null,
            mode: payload.advanceMode || "Cash",
            notes: "Advance collected during booking creation"
          })
        });
      }

      setModal(null);
      setActivePage("bookings");
      // Refresh after save so generated ids and DB-calculated fields are used.
      await refreshData(booking.id);
    } catch (error) {
      showSaveError("Could not save booking", error);
    } finally {
      setIsSaving(false);
    }
  }

  async function addMaterial(payload) {
    if (isBlank(payload.name)) {
      showRequiredMessage("material name");
      return;
    }
    if (isBlank(payload.category)) {
      showRequiredMessage("category");
      return;
    }
    if (isBlank(payload.unit)) {
      showRequiredMessage("unit");
      return;
    }

    setIsSaving(true);
    try {
      // Add to material master; future line-item modals use this item list.
      await apiRequest("/items", {
        method: "POST",
        body: JSON.stringify({
          name: payload.name.trim(),
          category: payload.category.trim(),
          unit: payload.unit.trim(),
          default_rate: Number(payload.rate) || 0,
          status: "Active"
        })
      });

      setModal(null);
      setActivePage("items");
      await refreshData();
    } catch (error) {
      showSaveError("Could not save material", error);
    } finally {
      setIsSaving(false);
    }
  }

  async function addEventType(payload) {
    if (isBlank(payload.name)) {
      showRequiredMessage("event name");
      return;
    }

    setIsSaving(true);
    try {
      await apiRequest("/event-types", {
        method: "POST",
        body: JSON.stringify({
          name: normalizeName(payload.name),
          status: "Active"
        })
      });

      setModal(null);
      setActivePage("events");
      await refreshData();
    } catch (error) {
      showSaveError("Could not save event", error);
    } finally {
      setIsSaving(false);
    }
  }

  async function ensureEventType(name) {
    const normalizedName = normalizeName(name);
    if (!normalizedName) return normalizedName;

    const existingEventType = eventTypeList.find(
      (eventType) => eventType.name.toLowerCase() === normalizedName.toLowerCase()
    );
    if (existingEventType) return existingEventType.name;

    const eventType = await apiRequest("/event-types", {
      method: "POST",
      body: JSON.stringify({
        name: normalizedName,
        status: "Active"
      })
    });
    return eventType.name;
  }

  async function addEvent(payload) {
    if (!selectedBookingId) {
      alert("Please create a booking before adding an event.");
      return;
    }
    if (isBlank(payload.name)) {
      showRequiredMessage("event name");
      return;
    }
    const normalizedEventName = normalizeName(payload.name);
    const duplicateEvent = selectedBooking?.events.some(
      (event) => event.name.trim().toLowerCase() === normalizedEventName.toLowerCase()
    );
    if (duplicateEvent) {
      alert("This event is already added to the selected booking.");
      return;
    }

    setIsSaving(true);
    try {
      const eventName = await ensureEventType(normalizedEventName);
      // Events are children of the currently selected booking.
      await apiRequest(`/bookings/${selectedBookingId}/events`, {
        method: "POST",
        body: JSON.stringify({
          name: eventName,
          event_date: payload.date || null,
          venue: isBlank(payload.venue) ? null : payload.venue.trim(),
          status: "Pending",
          line_items: []
        })
      });

      setModal(null);
      await refreshData(selectedBookingId);
    } catch (error) {
      showSaveError("Could not save event", error);
    } finally {
      setIsSaving(false);
    }
  }

  async function addLineItem(eventId, payload) {
    if (isBlank(payload.material)) {
      showRequiredMessage("material");
      return;
    }
    if (Number(payload.quantity) <= 0) {
      alert("Please add quantity greater than 0.");
      return;
    }
    if (Number(payload.rate) < 0 || isBlank(payload.rate)) {
      alert("Please add valid rate.");
      return;
    }

    setIsSaving(true);
    try {
      // Line items are children of events, so the endpoint is event-based.
      await apiRequest(`/bookings/events/${eventId}/line-items`, {
        method: "POST",
        body: JSON.stringify({
          material_name: payload.material.trim(),
          quantity: Number(payload.quantity) || 1,
          rate: Number(payload.rate) || 0
        })
      });

      setModal(null);
      await refreshData(selectedBookingId);
    } catch (error) {
      showSaveError("Could not save event material", error);
    } finally {
      setIsSaving(false);
    }
  }

  async function addPayment(payload) {
    if (!selectedBooking) {
      alert("Please create a booking before adding a payment.");
      return;
    }

    const totals = bookingTotals(selectedBooking, paymentList);
    const currentBalance = totals.balance;
    const amount = Number(payload.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      alert("Please add payment amount greater than 0.");
      return;
    }
    if (totals.subtotal > 0 && currentBalance <= 0) {
      alert("Payment is already done for this booking.");
      return;
    }
    if (totals.subtotal > 0 && amount > currentBalance) {
      alert("Payment amount cannot be greater than current balance.");
      return;
    }

    setIsSaving(true);
    try {
      // Payments are attached to the selected booking and immediately affect
      // the visible Status, Balance, and invoice totals after refresh.
      await apiRequest(`/bookings/${selectedBookingId}/payments`, {
        method: "POST",
        body: JSON.stringify({
          amount,
          payment_date: payload.date || null,
          mode: payload.mode,
          notes: payload.type
        })
      });

      setModal(null);
      await refreshData(selectedBookingId);
    } catch (error) {
      showSaveError("Could not save payment", error);
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteBooking(bookingId) {
    const booking = bookingList.find((currentBooking) => currentBooking.id === bookingId);
    if (!booking || !window.confirm(`Confirm delete booking "${booking.title}"?`)) return;

    setIsSaving(true);
    try {
      await apiRequest(`/bookings/${bookingId}`, { method: "DELETE" });
      setModal(null);
      setActivePage("bookings");
      await refreshData(null);
    } catch (error) {
      showSaveError("Could not mark booking inactive", error);
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteEvent(eventId) {
    const event = selectedBooking?.events.find((currentEvent) => currentEvent.id === eventId);
    if (!event || !window.confirm(`Confirm delete event "${event.name}"?`)) return;

    setIsSaving(true);
    try {
      await apiRequest(`/bookings/events/${eventId}`, { method: "DELETE" });
      await refreshData(selectedBookingId);
    } catch (error) {
      showSaveError("Could not mark event inactive", error);
    } finally {
      setIsSaving(false);
    }
  }

  async function sendBillMail(bookingId) {
    setIsSaving(true);
    try {
      const response = await apiRequest(`/bookings/${bookingId}/send-mail`, {
        method: "POST",
        body: JSON.stringify({})
      });
      alert(response.message || "Bill email sent.");
    } catch (error) {
      showSaveError("Could not send bill email", error);
    } finally {
      setIsSaving(false);
    }
  }

  async function saveCompanySettings(nextSettings) {
    setIsSaving(true);
    try {
      const apiSettings = await apiRequest("/company-settings", {
        method: "PUT",
        body: JSON.stringify(mapCompanySettingsToApi(nextSettings))
      });
      setCompanySettings(mapCompanySettingsFromApi(apiSettings));
      alert("Company settings saved.");
    } catch (error) {
      showSaveError("Could not save company settings", error);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">PFX</div>
          <div>
            <strong>Prasad FX Lights</strong>
            <span>Billing Desk</span>
          </div>
        </div>

        <nav className="side-nav" aria-label="Main navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={activePage === item.id ? "active" : ""}
                onClick={() => setActivePage(item.id)}
                type="button"
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <span className="eyebrow">Single device billing system</span>
            <h1>{pageTitle(activePage)}</h1>
            <span className="api-status">{apiStatus}</span>
          </div>
          <div className="top-actions">
            <label className="search-box">
              <Search size={17} />
              <input
                placeholder="Search client name or mobile"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
              />
            </label>
            <button className="primary-action" onClick={() => setModal({ type: "booking" })} type="button">
              <Plus size={18} />
              New Booking
            </button>
          </div>
        </header>

        {/* Page switches keep each major screen in its own component. */}
        {activePage === "dashboard" && <Dashboard bookings={bookingList} items={itemList} payments={paymentList} />}
        {activePage === "bookings" && (
          <BookingsPage
            bookings={filteredBookings}
            selectedBooking={selectedBooking}
            selectedBookingId={selectedBookingId}
            onSelectBooking={setSelectedBookingId}
            payments={paymentList}
            onAddBooking={() => setModal({ type: "booking" })}
            onAddEvent={() => setModal({ type: "event" })}
            onAddLineItem={(eventId) => setModal({ type: "line", eventId })}
            onAddPayment={() => setModal({ type: "payment" })}
            onDeleteBooking={deleteBooking}
            onDeleteEvent={deleteEvent}
            isSaving={isSaving}
            onOpenInvoice={() => setActivePage("invoice")}
          />
        )}
        {activePage === "invoice" && (
          <InvoicePreview
            booking={selectedBooking}
            companySettings={companySettings}
            isSaving={isSaving}
            onSendMail={sendBillMail}
            payments={paymentList}
          />
        )}
        {activePage === "events" && (
          <EventTypesPage eventTypes={eventTypeList} onAddEventType={() => setModal({ type: "eventType" })} />
        )}
        {activePage === "items" && <ItemsPage items={itemList} onAddMaterial={() => setModal({ type: "material" })} />}
        {activePage === "settings" && (
          <SettingsPage
            isSaving={isSaving}
            onChange={setCompanySettings}
            onSave={saveCompanySettings}
            settings={companySettings}
          />
        )}
      </main>

      {modal?.type === "booking" && (
        <BookingModal
          defaultAdvance={companySettings.defaultAdvance}
          isSaving={isSaving}
          onClose={() => setModal(null)}
          onSubmit={addBooking}
        />
      )}
      {modal?.type === "material" && (
        <MaterialModal isSaving={isSaving} onClose={() => setModal(null)} onSubmit={addMaterial} />
      )}
      {modal?.type === "eventType" && (
        <EventTypeModal isSaving={isSaving} onClose={() => setModal(null)} onSubmit={addEventType} />
      )}
      {modal?.type === "event" && (
        <EventModal
          eventTypes={eventTypeList}
          isSaving={isSaving}
          onClose={() => setModal(null)}
          onSubmit={addEvent}
        />
      )}
      {modal?.type === "line" && (
        <LineItemModal
          items={itemList}
          isSaving={isSaving}
          onClose={() => setModal(null)}
          onSubmit={(payload) => addLineItem(modal.eventId, payload)}
        />
      )}
      {modal?.type === "payment" && (
        <PaymentModal
          balance={bookingTotals(selectedBooking, paymentList).balance}
          isSaving={isSaving}
          onClose={() => setModal(null)}
          onSubmit={addPayment}
        />
      )}
    </div>
  );
}

function pageTitle(page) {
  // Translate internal page ids into user-facing headings.
  const titles = {
    dashboard: "Dashboard",
    bookings: "Wedding Bookings",
    invoice: "Final Bill Preview",
    events: "Events",
    items: "Material Master",
    settings: "Settings"
  };
  return titles[page];
}

function Dashboard({ bookings, items, payments }) {
  // Dashboard metrics are derived from the same bookingTotals helper as invoices.
  const totalRevenue = bookings.reduce((sum, booking) => sum + bookingTotals(booking, payments).subtotal, 0);
  const totalBalance = bookings.reduce((sum, booking) => sum + bookingTotals(booking, payments).balance, 0);
  const upcomingEvents = bookings.flatMap((booking) =>
    booking.events.map((event) => ({ ...event, bookingTitle: booking.title }))
  );

  return (
    <section className="page-grid">
      <div className="metric-row">
        <MetricCard icon={IndianRupee} label="Booked Amount" value={formatCurrency(totalRevenue)} />
        <MetricCard icon={FileText} label="Pending Balance" value={formatCurrency(totalBalance)} />
        <MetricCard icon={Users} label="Active Bookings" value={bookings.length} />
        <MetricCard icon={Sparkles} label="FX Materials" value={items.length} />
      </div>

      <section className="surface">
        <div className="section-heading">
          <h2>Upcoming Event Entries</h2>
          <button className="ghost-button" type="button">View Calendar</button>
        </div>
        <div className="event-list">
          {upcomingEvents.map((event) => (
            <article className="event-row" key={event.id}>
              <div>
                <strong>{event.name}</strong>
                <span>{event.bookingTitle}</span>
              </div>
              <div>{event.venue}</div>
              <div>{event.date}</div>
              <strong>{formatCurrency(event.lines.reduce((sum, line) => sum + line.quantity * line.rate, 0))}</strong>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

function MetricCard({ icon: Icon, label, value }) {
  // Icon is passed as a React component from lucide-react.
  return (
    <article className="metric-card">
      <Icon size={22} />
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function BookingsPage({
  bookings,
  selectedBooking,
  selectedBookingId,
  onSelectBooking,
  payments,
  onAddBooking,
  onAddEvent,
  onAddLineItem,
  onAddPayment,
  onDeleteBooking,
  onDeleteEvent,
  isSaving,
  onOpenInvoice
}) {
  // Left side selects a booking; right side renders the selected booking details.
  return (
    <section className="split-layout">
      <aside className="surface booking-list">
        <div className="section-heading">
          <h2>Bookings</h2>
          <button className="icon-button" onClick={onAddBooking} title="Add booking" type="button">
            <Plus size={17} />
          </button>
        </div>
        {bookings.map((booking) => {
          const totals = bookingTotals(booking, payments);
          const paymentStatus = paymentStatusFromBalance(totals.balance);
          return (
            <button
              className={booking.id === selectedBookingId ? "booking-card selected" : "booking-card"}
              key={booking.id}
              onClick={() => onSelectBooking(booking.id)}
              type="button"
            >
              <strong>{booking.title}</strong>
              <span>{booking.client.name} · {booking.client.mobile}</span>
              <small>{booking.startDate} to {booking.endDate}</small>
              <b>{paymentStatus}: {formatCurrency(totals.balance)} balance</b>
            </button>
          );
        })}
        {bookings.length === 0 && (
          <div className="empty-panel compact-empty">
            <strong>No bookings yet.</strong>
            <span>Create the first booking to add events, materials, and payments.</span>
          </div>
        )}
      </aside>

      {selectedBooking ? (
        <BookingDetail
          booking={selectedBooking}
          onAddEvent={onAddEvent}
          onAddLineItem={onAddLineItem}
          onAddPayment={onAddPayment}
          onDeleteBooking={onDeleteBooking}
          onDeleteEvent={onDeleteEvent}
          isSaving={isSaving}
          onOpenInvoice={onOpenInvoice}
          payments={payments}
        />
      ) : (
        <EmptyBookingState onAddBooking={onAddBooking} />
      )}
    </section>
  );
}

function EmptyBookingState({ onAddBooking }) {
  return (
    <section className="surface empty-panel">
      <h2>No booking selected</h2>
      <p>Create a booking first. After that you can add events, materials, payments, and print the final bill.</p>
      <button className="primary-action" onClick={onAddBooking} type="button">
        <Plus size={18} />
        New Booking
      </button>
    </section>
  );
}

function BookingDetail({
  booking,
  payments,
  onAddEvent,
  onAddLineItem,
  onAddPayment,
  onDeleteBooking,
  onDeleteEvent,
  isSaving,
  onOpenInvoice
}) {
  // Totals are recalculated whenever selected booking or payment props change.
  const totals = bookingTotals(booking, payments);
  const paymentStatus = paymentStatusFromBalance(totals.balance);

  return (
    <section className="surface detail-pane">
      <div className="detail-header">
        <div>
          <span className="eyebrow">Booking #{booking.bookingNo}</span>
          <h2>{booking.title}</h2>
          <p>{booking.client.name} · {booking.client.mobile} · {booking.client.address}</p>
        </div>
        <div className="amount-stack">
          <span>Total</span>
          <strong>{formatCurrency(totals.subtotal)}</strong>
          <div className="booking-actions">
            <button className="primary-action" onClick={onOpenInvoice} type="button">
              <ReceiptText size={17} />
              Print Final Bill
            </button>
            <button
              className="icon-button danger"
              disabled={isSaving}
              onClick={() => onDeleteBooking(booking.id)}
              title="Delete booking"
              type="button"
            >
              <Trash2 size={17} />
            </button>
          </div>
        </div>
      </div>

      <div className="summary-strip">
        <span>Advance: <strong>{formatCurrency(totals.paid)}</strong></span>
        <span>Balance: <strong>{formatCurrency(totals.balance)}</strong></span>
        <span>Status: <strong>{paymentStatus}</strong></span>
        <button className="ghost-button compact" onClick={onAddPayment} type="button">
          <Landmark size={16} />
          Add Payment
        </button>
        <button className="ghost-button compact" onClick={onAddEvent} type="button">
          <Plus size={16} />
          Add Event
        </button>
      </div>

      <div className="event-builder">
        {booking.events.map((event) => (
          <article className="event-panel" key={event.id}>
            <div className="event-panel-head">
              <div>
                <h3>{event.name}</h3>
                <span>{event.date} · {event.venue}</span>
              </div>
              <div className="event-actions">
                <button className="ghost-button" onClick={() => onAddLineItem(event.id)} type="button">Add Material</button>
                <button
                  className="icon-button danger"
                  disabled={isSaving}
                  onClick={() => onDeleteEvent(event.id)}
                  title="Delete event"
                  type="button"
                >
                  <Trash2 size={17} />
                </button>
              </div>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Material</th>
                  <th>Qty</th>
                  <th>Rate</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {event.lines.map((line) => (
                  <tr key={line.id}>
                    <td>{line.material}</td>
                    <td>{line.quantity}</td>
                    <td>{formatCurrency(line.rate)}</td>
                    <td>{formatCurrency(line.quantity * line.rate)}</td>
                  </tr>
                ))}
                {event.lines.length === 0 && (
                  <tr>
                    <td colSpan="4" className="empty-cell">No material added yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </article>
        ))}
      </div>
    </section>
  );
}

function InvoicePreview({ booking, companySettings, isSaving, onSendMail, payments }) {
  if (!booking) {
    return (
      <section className="surface empty-panel">
        <h2>No invoice available</h2>
        <p>Create a booking before opening the invoice preview.</p>
      </section>
    );
  }

  // Invoice uses the same selected booking but formats it as a print-ready page.
  const totals = bookingTotals(booking, payments);
  const bookingPayments = payments.filter((payment) => payment.bookingId === booking.id);
  const paymentStatus = paymentStatusFromBalance(totals.balance);

  return (
    <section className="invoice-stage">
      <div className="invoice-toolbar">
        <span className="print-context">Printing bill for {booking.client.name}</span>
        <div className="invoice-actions">
          <button className="ghost-button" disabled={isSaving} onClick={() => onSendMail(booking.id)} type="button">
            <Mail size={16} />
            Send Mail
          </button>
          <button className="primary-action" onClick={() => window.print()} type="button">Print Bill</button>
        </div>
      </div>

      <div className="invoice-page">
        <header className="bill-header">
          <div className="bill-brand">
            <div className="large-logo">{companySettings.invoicePrefix}</div>
            <div>
              <span className="eyebrow">Final Bill</span>
              <h2>{companySettings.companyName}</h2>
              <p>Laser, LED, Sharpee and FX lighting supplier</p>
            </div>
          </div>
          <div className="bill-id-card">
            <span>Invoice No.</span>
            <strong>{companySettings.invoicePrefix}-{booking.bookingNo}</strong>
            <small>{booking.startDate}</small>
          </div>
        </header>

        <section className="bill-info-grid">
          <div>
            <span className="bill-label">Bill To</span>
            <h3>{booking.client.name}</h3>
            <p>{booking.client.mobile}</p>
            <p>{booking.client.address}</p>
          </div>
          <div>
            <span className="bill-label">Booking</span>
            <h3>{booking.title}</h3>
            <p>{booking.startDate} to {booking.endDate}</p>
            <p>{booking.events.length} linked event entries</p>
          </div>
          <div>
            <span className="bill-label">Amount Due</span>
            <strong className="bill-due">{formatCurrency(totals.balance)}</strong>
            <p>Status: {paymentStatus}</p>
          </div>
        </section>

        <section className="bill-events">
          {booking.events.map((event, index) => {
            const eventTotal = event.lines.reduce(
              (sum, line) => sum + line.quantity * line.rate,
              0
            );

            return (
              <article className="bill-event" key={event.id}>
                <div className="bill-event-head">
                  <div>
                    <span>Event {index + 1}</span>
                    <h3>{event.name}</h3>
                  </div>
                  <div>
                    <strong>{event.date}</strong>
                    <small>{event.venue}</small>
                  </div>
                </div>

                <table className="bill-table">
                  <thead>
                    <tr>
                      <th>Material</th>
                      <th>Qty</th>
                      <th>Rate</th>
                      <th>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {event.lines.map((line) => (
                      <tr key={line.id}>
                        <td>{line.material}</td>
                        <td>{line.quantity}</td>
                        <td>{formatCurrency(line.rate)}</td>
                        <td>{formatCurrency(line.quantity * line.rate)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan="3">Event Subtotal</td>
                      <td>{formatCurrency(eventTotal)}</td>
                    </tr>
                  </tfoot>
                </table>
              </article>
            );
          })}
        </section>

        <section className="bill-bottom">
          <div className="payment-box">
            <h3>Payments</h3>
            {bookingPayments.map((payment) => (
              <div className="payment-row" key={payment.id}>
                <span>{payment.date}</span>
                <span>{payment.mode}</span>
                <strong>{formatCurrency(payment.amount)}</strong>
              </div>
            ))}
            {bookingPayments.length === 0 && <p>No advance payment recorded.</p>}
          </div>

          <div className="bill-totals">
            <div><span>Subtotal</span><strong>{formatCurrency(totals.subtotal)}</strong></div>
            <div><span>Advance Paid</span><strong>{formatCurrency(totals.paid)}</strong></div>
            <div className="grand-row"><span>Balance Due</span><strong>{formatCurrency(totals.balance)}</strong></div>
          </div>
        </section>

        <div className="bill-note">
          <strong>Thank you for your business.</strong>
          <span>All materials are billed event-wise and linked under this wedding booking.</span>
        </div>
      </div>
    </section>
  );
}

function ItemsPage({ items, onAddMaterial }) {
  // Material master table feeds the Add Event Material dropdown.
  return (
    <section className="surface">
      <div className="section-heading">
        <h2>FX Light Materials</h2>
        <button className="primary-action" onClick={onAddMaterial} type="button">
          <Plus size={18} />
          Add Material
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Material</th>
            <th>Category</th>
            <th>Unit</th>
            <th>Default Rate</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.name}</td>
              <td>{item.category}</td>
              <td>{item.unit}</td>
              <td>{formatCurrency(item.rate)}</td>
              <td><span className="status-pill">{item.status}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function EventTypesPage({ eventTypes, onAddEventType }) {
  return (
    <section className="surface">
      <div className="section-heading">
        <h2>Events</h2>
        <button className="primary-action" onClick={onAddEventType} type="button">
          <Plus size={18} />
          Add Event
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Event</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {eventTypes.length > 0 ? eventTypes.map((eventType) => (
            <tr key={eventType.id}>
              <td>{eventType.name}</td>
              <td><span className="status-pill">{eventType.status}</span></td>
            </tr>
          )) : (
            <tr>
              <td colSpan="2" className="empty-cell">No events added yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

function Modal({ title, onClose, children }) {
  // Generic wrapper used by all forms so modal structure and close button match.
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-card" role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="icon-button" onClick={onClose} title="Close" type="button">
            <X size={18} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

function BookingModal({ defaultAdvance, isSaving, onClose, onSubmit }) {
  // Local form state is submitted to App.addBooking(), which performs API calls.
  const [form, setForm] = useState({
    title: "",
    clientName: "",
    mobile: "",
    address: "",
    startDate: "",
    endDate: "",
    advance: defaultAdvance || "",
    advanceMode: "Cash"
  });

  return (
    <Modal title="New Booking" onClose={onClose}>
      <form className="modal-form" onSubmit={(event) => {
        event.preventDefault();
        onSubmit(form);
      }}>
        <label>Booking Name<input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Patel Wedding" /></label>
        <label>Client Name<input required value={form.clientName} onChange={(event) => setForm({ ...form, clientName: event.target.value })} /></label>
        <label>
          Mobile
          <input
            inputMode="numeric"
            maxLength="10"
            pattern="[0-9]{10}"
            required
            value={form.mobile}
            onChange={(event) => setForm({ ...form, mobile: mobileDigits(event.target.value) })}
          />
        </label>
        <label>Address<input value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} /></label>
        <label>Start Date<input type="date" value={form.startDate} onChange={(event) => setForm({ ...form, startDate: event.target.value })} /></label>
        <label>End Date<input type="date" value={form.endDate} onChange={(event) => setForm({ ...form, endDate: event.target.value })} /></label>
        <label>Advance<input min="0" type="number" value={form.advance} onChange={(event) => setForm({ ...form, advance: event.target.value })} /></label>
        <label>
          Advance Mode
          <select value={form.advanceMode} onChange={(event) => setForm({ ...form, advanceMode: event.target.value })}>
            <option>Cash</option>
            <option>UPI</option>
            <option>Bank Transfer</option>
            <option>Cheque</option>
          </select>
        </label>
        <div className="modal-actions">
          <button className="ghost-button" disabled={isSaving} onClick={onClose} type="button">Cancel</button>
          <button className="primary-action" disabled={isSaving} type="submit">{isSaving ? "Saving..." : "Create Booking"}</button>
        </div>
      </form>
    </Modal>
  );
}

function MaterialModal({ isSaving, onClose, onSubmit }) {
  // Material form creates a reusable rate/unit entry in the backend.
  const [form, setForm] = useState({ name: "", category: "FX Light", unit: "Piece", rate: "" });

  return (
    <Modal title="Add Material" onClose={onClose}>
      <form className="modal-form" onSubmit={(event) => {
        event.preventDefault();
        onSubmit(form);
      }}>
        <label>Material Name<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Laser" /></label>
        <label>Category<input value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} /></label>
        <label>Unit<input value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} /></label>
        <label>Default Rate<input min="0" type="number" value={form.rate} onChange={(event) => setForm({ ...form, rate: event.target.value })} /></label>
        <div className="modal-actions">
          <button className="ghost-button" disabled={isSaving} onClick={onClose} type="button">Cancel</button>
          <button className="primary-action" disabled={isSaving} type="submit">{isSaving ? "Saving..." : "Add Material"}</button>
        </div>
      </form>
    </Modal>
  );
}

function EventTypeModal({ isSaving, onClose, onSubmit }) {
  const [form, setForm] = useState({ name: "" });

  return (
    <Modal title="Add Event" onClose={onClose}>
      <form className="modal-form" onSubmit={(event) => {
        event.preventDefault();
        onSubmit({ name: normalizeName(form.name) });
      }}>
        <label>Event Name<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Sangeet" /></label>
        <div className="modal-actions">
          <button className="ghost-button" disabled={isSaving} onClick={onClose} type="button">Cancel</button>
          <button className="primary-action" disabled={isSaving} type="submit">{isSaving ? "Saving..." : "Add Event"}</button>
        </div>
      </form>
    </Modal>
  );
}

function EventModal({ eventTypes, isSaving, onClose, onSubmit }) {
  // Event form attaches a new event to the selected booking.
  const [form, setForm] = useState({ name: "", date: "", venue: "" });

  return (
    <Modal title="Add Event" onClose={onClose}>
      <form className="modal-form" onSubmit={(event) => {
        event.preventDefault();
        onSubmit({ ...form, name: normalizeName(form.name) });
      }}>
        <label>
          Event Name
          <input
            list="event-type-options"
            required
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
            placeholder="Select or type event"
          />
          <datalist id="event-type-options">
            {eventTypes.map((eventType) => (
              <option key={eventType.id} value={eventType.name} />
            ))}
          </datalist>
        </label>
        <label>Date<input type="date" value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} /></label>
        <label>Venue<input value={form.venue} onChange={(event) => setForm({ ...form, venue: event.target.value })} /></label>
        <div className="modal-actions">
          <button className="ghost-button" disabled={isSaving} onClick={onClose} type="button">Cancel</button>
          <button className="primary-action" disabled={isSaving} type="submit">{isSaving ? "Saving..." : "Add Event"}</button>
        </div>
      </form>
    </Modal>
  );
}

function LineItemModal({ items, isSaving, onClose, onSubmit }) {
  // Default to the first material so the user can quickly add common items.
  const firstItem = items[0] ?? { name: "", rate: 0 };
  const [form, setForm] = useState({
    material: firstItem.name,
    quantity: "1",
    rate: String(firstItem.rate)
  });

  function selectMaterial(name) {
    // When material changes, copy its default rate into the editable rate field.
    const selectedItem = items.find((item) => item.name === name);
    setForm({
      ...form,
      material: name,
      rate: selectedItem ? String(selectedItem.rate) : form.rate
    });
  }

  return (
    <Modal title="Add Event Material" onClose={onClose}>
      <form className="modal-form" onSubmit={(event) => {
        event.preventDefault();
        onSubmit(form);
      }}>
        <label>
          Material
          <select required value={form.material} onChange={(event) => selectMaterial(event.target.value)}>
            {items.map((item) => (
              <option key={item.id} value={item.name}>{item.name}</option>
            ))}
          </select>
        </label>
        <label>Quantity<input min="1" type="number" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} /></label>
        <label>Rate<input min="0" type="number" value={form.rate} onChange={(event) => setForm({ ...form, rate: event.target.value })} /></label>
        <div className="modal-actions">
          <button className="ghost-button" disabled={isSaving} onClick={onClose} type="button">Cancel</button>
          <button className="primary-action" disabled={isSaving} type="submit">{isSaving ? "Saving..." : "Add To Event"}</button>
        </div>
      </form>
    </Modal>
  );
}

function PaymentModal({ balance, isSaving, onClose, onSubmit }) {
  // Payment form supports partial payments and final payment against the balance.
  const safeBalance = Math.max(balance, 0);
  const hasBalance = safeBalance > 0;
  const [form, setForm] = useState({
    type: "Partial Payment",
    amount: "",
    mode: "Cash",
    date: todayInputDate()
  });

  function selectPaymentType(type) {
    setForm({
      ...form,
      type,
      amount: type === "Final Payment" && hasBalance ? String(safeBalance) : form.amount
    });
  }

  return (
    <Modal title="Add Payment" onClose={onClose}>
      <form className="modal-form" onSubmit={(event) => {
        event.preventDefault();
        onSubmit(form);
      }}>
        <label>
          Payment Type
          <select value={form.type} onChange={(event) => selectPaymentType(event.target.value)}>
            <option>Partial Payment</option>
            <option>Final Payment</option>
          </select>
        </label>
        <label>Amount<input max={hasBalance ? safeBalance : undefined} min="1" required type="number" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} /></label>
        <label>
          Mode
          <select value={form.mode} onChange={(event) => setForm({ ...form, mode: event.target.value })}>
            <option>Cash</option>
            <option>UPI</option>
            <option>Bank Transfer</option>
            <option>Cheque</option>
          </select>
        </label>
        <label>Date<input type="date" value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} /></label>
        <div className="payment-balance-note">Current balance: <strong>{formatCurrency(safeBalance)}</strong></div>
        <div className="modal-actions">
          <button className="ghost-button" disabled={isSaving} onClick={onClose} type="button">Cancel</button>
          <button className="primary-action" disabled={isSaving} type="submit">{isSaving ? "Saving..." : "Save Payment"}</button>
        </div>
      </form>
    </Modal>
  );
}

function SettingsPage({ isSaving, settings, onChange, onSave }) {
  function updateSetting(field, value) {
    onChange({
      ...settings,
      [field]: value
    });
  }

  return (
    <section className="surface settings-panel">
      <div className="section-heading">
        <h2>Company Settings</h2>
        <button className="primary-action" disabled={isSaving} onClick={() => onSave(settings)} type="button">
          {isSaving ? "Saving..." : "Save"}
        </button>
      </div>
      <div className="form-grid settings-form">
        <label>Company Name<input value={settings.companyName} onChange={(event) => updateSetting("companyName", event.target.value)} /></label>
        <label>Invoice Prefix<input value={settings.invoicePrefix} onChange={(event) => updateSetting("invoicePrefix", event.target.value)} /></label>
        <label>Owner Mobile<input value={settings.ownerMobile} onChange={(event) => updateSetting("ownerMobile", event.target.value)} /></label>
        <label>Default Advance<input min="0" type="number" value={settings.defaultAdvance} onChange={(event) => updateSetting("defaultAdvance", event.target.value)} /></label>
        <label>Send Mail<input type="email" value={settings.sendMail} onChange={(event) => updateSetting("sendMail", event.target.value)} /></label>
        <label>Receiver Mail<input type="email" value={settings.recvMail} onChange={(event) => updateSetting("recvMail", event.target.value)} /></label>
      </div>
    </section>
  );
}

// Mount the React application into frontend/index.html.
createRoot(document.getElementById("root")).render(<App />);
