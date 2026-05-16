import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  CalendarDays,
  FileText,
  Gauge,
  IndianRupee,
  LibraryBig,
  Plus,
  ReceiptText,
  Search,
  Settings,
  Sparkles,
  Users,
  X
} from "lucide-react";
import { bookings as initialBookings, inventoryItems as initialItems, payments as initialPayments } from "./data/sampleData";
import "./styles/app.css";

const API_BASE_URL = "http://127.0.0.1:8000/api";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: Gauge },
  { id: "bookings", label: "Bookings", icon: CalendarDays },
  { id: "invoice", label: "Invoice Preview", icon: ReceiptText },
  { id: "items", label: "Material Master", icon: LibraryBig },
  { id: "settings", label: "Settings", icon: Settings }
];

function formatCurrency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(value);
}

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

function nextBookingNo(bookings) {
  const maxBookingNo = Math.max(1000, ...bookings.map((booking) => Number(booking.bookingNo) || 1000));
  return String(maxBookingNo + 1);
}

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

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed: ${response.status}`);
  }

  return response.json();
}

function bookingTotals(booking, paymentList = initialPayments) {
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

function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [bookingList, setBookingList] = useState(initialBookings);
  const [itemList, setItemList] = useState(initialItems);
  const [paymentList, setPaymentList] = useState(initialPayments);
  const [selectedBookingId, setSelectedBookingId] = useState(initialBookings[0].id);
  const [modal, setModal] = useState(null);
  const [apiStatus, setApiStatus] = useState("Connecting to backend...");
  const [isSaving, setIsSaving] = useState(false);
  const selectedBooking = useMemo(
    () => bookingList.find((booking) => booking.id === selectedBookingId) ?? bookingList[0],
    [bookingList, selectedBookingId]
  );

  useEffect(() => {
    refreshData();
  }, []);

  async function refreshData(preferredBookingId = selectedBookingId) {
    try {
      const [apiBookings, apiItems] = await Promise.all([
        apiRequest("/bookings"),
        apiRequest("/items")
      ]);
      const mappedBookings = apiBookings.map(mapBookingFromApi);
      const mappedPayments = mappedBookings.flatMap((booking) => booking.payments);

      setBookingList(mappedBookings);
      setItemList(apiItems.map(mapItemFromApi));
      setPaymentList(mappedPayments);
      setSelectedBookingId(
        mappedBookings.some((booking) => booking.id === preferredBookingId)
          ? preferredBookingId
          : mappedBookings[0]?.id
      );
      setApiStatus("Connected to MySQL");
    } catch (error) {
      setApiStatus("Backend offline, showing local sample data");
    }
  }

  async function addBooking(payload) {
    setIsSaving(true);
    try {
      const client = await apiRequest("/clients", {
        method: "POST",
        body: JSON.stringify({
          name: payload.clientName,
          mobile: payload.mobile,
          address: payload.address || null
        })
      });
      const booking = await apiRequest("/bookings", {
        method: "POST",
        body: JSON.stringify({
          booking_no: nextBookingNo(bookingList),
          title: payload.title,
          client_id: client.id,
          start_date: payload.startDate || null,
          end_date: payload.endDate || null,
          status: "Draft",
          events: []
        })
      });

      setModal(null);
      setActivePage("bookings");
      await refreshData(booking.id);
    } catch (error) {
      alert("Could not save booking. Please make sure backend is running.");
    } finally {
      setIsSaving(false);
    }
  }

  async function addMaterial(payload) {
    setIsSaving(true);
    try {
      await apiRequest("/items", {
        method: "POST",
        body: JSON.stringify({
          name: payload.name,
          category: payload.category,
          unit: payload.unit,
          default_rate: Number(payload.rate) || 0,
          status: "Active"
        })
      });

      setModal(null);
      setActivePage("items");
      await refreshData();
    } catch (error) {
      alert("Could not save material. Check if the material already exists and backend is running.");
    } finally {
      setIsSaving(false);
    }
  }

  async function addEvent(payload) {
    setIsSaving(true);
    try {
      await apiRequest(`/bookings/${selectedBookingId}/events`, {
        method: "POST",
        body: JSON.stringify({
          name: payload.name,
          event_date: payload.date || null,
          venue: payload.venue || null,
          line_items: []
        })
      });

      setModal(null);
      await refreshData(selectedBookingId);
    } catch (error) {
      alert("Could not save event. Please make sure backend is running.");
    } finally {
      setIsSaving(false);
    }
  }

  async function addLineItem(eventId, payload) {
    setIsSaving(true);
    try {
      await apiRequest(`/bookings/events/${eventId}/line-items`, {
        method: "POST",
        body: JSON.stringify({
          material_name: payload.material,
          quantity: Number(payload.quantity) || 1,
          rate: Number(payload.rate) || 0
        })
      });

      setModal(null);
      await refreshData(selectedBookingId);
    } catch (error) {
      alert("Could not save event material. Please make sure backend is running.");
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
              <input placeholder="Search client, booking, mobile" />
            </label>
            <button className="primary-action" onClick={() => setModal({ type: "booking" })} type="button">
              <Plus size={18} />
              New Booking
            </button>
          </div>
        </header>

        {activePage === "dashboard" && <Dashboard bookings={bookingList} items={itemList} payments={paymentList} />}
        {activePage === "bookings" && (
          <BookingsPage
            bookings={bookingList}
            selectedBooking={selectedBooking}
            selectedBookingId={selectedBookingId}
            onSelectBooking={setSelectedBookingId}
            payments={paymentList}
            onAddBooking={() => setModal({ type: "booking" })}
            onAddEvent={() => setModal({ type: "event" })}
            onAddLineItem={(eventId) => setModal({ type: "line", eventId })}
            onOpenInvoice={() => setActivePage("invoice")}
          />
        )}
        {activePage === "invoice" && <InvoicePreview booking={selectedBooking} payments={paymentList} />}
        {activePage === "items" && <ItemsPage items={itemList} onAddMaterial={() => setModal({ type: "material" })} />}
        {activePage === "settings" && <SettingsPage />}
      </main>

      {modal?.type === "booking" && (
        <BookingModal isSaving={isSaving} onClose={() => setModal(null)} onSubmit={addBooking} />
      )}
      {modal?.type === "material" && (
        <MaterialModal isSaving={isSaving} onClose={() => setModal(null)} onSubmit={addMaterial} />
      )}
      {modal?.type === "event" && (
        <EventModal isSaving={isSaving} onClose={() => setModal(null)} onSubmit={addEvent} />
      )}
      {modal?.type === "line" && (
        <LineItemModal
          items={itemList}
          isSaving={isSaving}
          onClose={() => setModal(null)}
          onSubmit={(payload) => addLineItem(modal.eventId, payload)}
        />
      )}
    </div>
  );
}

function pageTitle(page) {
  const titles = {
    dashboard: "Dashboard",
    bookings: "Wedding Bookings",
    invoice: "Final Bill Preview",
    items: "Material Master",
    settings: "Settings"
  };
  return titles[page];
}

function Dashboard({ bookings, items, payments }) {
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
  onOpenInvoice
}) {
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
              <b>{formatCurrency(totals.balance)} pending</b>
            </button>
          );
        })}
      </aside>

      <BookingDetail
        booking={selectedBooking}
        onAddEvent={onAddEvent}
        onAddLineItem={onAddLineItem}
        onOpenInvoice={onOpenInvoice}
        payments={payments}
      />
    </section>
  );
}

function BookingDetail({ booking, payments, onAddEvent, onAddLineItem, onOpenInvoice }) {
  const totals = bookingTotals(booking, payments);

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
          <button className="primary-action" onClick={onOpenInvoice} type="button">
            <ReceiptText size={17} />
            Print Final Bill
          </button>
        </div>
      </div>

      <div className="summary-strip">
        <span>Advance: <strong>{formatCurrency(totals.paid)}</strong></span>
        <span>Balance: <strong>{formatCurrency(totals.balance)}</strong></span>
        <span>Status: <strong>{booking.status}</strong></span>
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
              <button className="ghost-button" onClick={() => onAddLineItem(event.id)} type="button">Add Material</button>
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

function InvoicePreview({ booking, payments }) {
  const totals = bookingTotals(booking, payments);
  const bookingPayments = payments.filter((payment) => payment.bookingId === booking.id);

  return (
    <section className="invoice-stage">
      <div className="invoice-toolbar">
        <span className="print-context">Printing bill for {booking.client.name}</span>
        <button className="primary-action" onClick={() => window.print()} type="button">Print Bill</button>
      </div>

      <div className="invoice-page">
        <header className="bill-header">
          <div className="bill-brand">
            <div className="large-logo">PFX</div>
            <div>
              <span className="eyebrow">Final Bill</span>
              <h2>Prasad FX Lights</h2>
              <p>Laser, LED, Sharpee and FX lighting supplier</p>
            </div>
          </div>
          <div className="bill-id-card">
            <span>Invoice No.</span>
            <strong>PFX-{booking.bookingNo}</strong>
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
            <p>Status: {booking.status}</p>
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

function Modal({ title, onClose, children }) {
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

function BookingModal({ isSaving, onClose, onSubmit }) {
  const [form, setForm] = useState({
    title: "",
    clientName: "",
    mobile: "",
    address: "",
    startDate: "",
    endDate: ""
  });

  return (
    <Modal title="New Booking" onClose={onClose}>
      <form className="modal-form" onSubmit={(event) => {
        event.preventDefault();
        onSubmit(form);
      }}>
        <label>Booking Name<input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Patel Wedding" /></label>
        <label>Client Name<input required value={form.clientName} onChange={(event) => setForm({ ...form, clientName: event.target.value })} /></label>
        <label>Mobile<input required value={form.mobile} onChange={(event) => setForm({ ...form, mobile: event.target.value })} /></label>
        <label>Address<input value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} /></label>
        <label>Start Date<input type="date" value={form.startDate} onChange={(event) => setForm({ ...form, startDate: event.target.value })} /></label>
        <label>End Date<input type="date" value={form.endDate} onChange={(event) => setForm({ ...form, endDate: event.target.value })} /></label>
        <div className="modal-actions">
          <button className="ghost-button" disabled={isSaving} onClick={onClose} type="button">Cancel</button>
          <button className="primary-action" disabled={isSaving} type="submit">{isSaving ? "Saving..." : "Create Booking"}</button>
        </div>
      </form>
    </Modal>
  );
}

function MaterialModal({ isSaving, onClose, onSubmit }) {
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

function EventModal({ isSaving, onClose, onSubmit }) {
  const [form, setForm] = useState({ name: "", date: "", venue: "" });

  return (
    <Modal title="Add Event" onClose={onClose}>
      <form className="modal-form" onSubmit={(event) => {
        event.preventDefault();
        onSubmit(form);
      }}>
        <label>Event Name<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Sangeet, Haldi, Saptpadi" /></label>
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
  const firstItem = items[0] ?? { name: "", rate: 0 };
  const [form, setForm] = useState({
    material: firstItem.name,
    quantity: "1",
    rate: String(firstItem.rate)
  });

  function selectMaterial(name) {
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

function SettingsPage() {
  return (
    <section className="surface settings-panel">
      <h2>Company Settings</h2>
      <div className="form-grid">
        <label>Company Name<input defaultValue="Prasad FX Lights" /></label>
        <label>Invoice Prefix<input defaultValue="PFX" /></label>
        <label>Owner Mobile<input defaultValue="+91 98765 43210" /></label>
        <label>Default Advance<input defaultValue="0" /></label>
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
