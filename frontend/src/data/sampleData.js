// Local fallback bookings. The app shows these when the backend is not running,
// and then replaces them with API data after refreshData() succeeds.
export const bookings = [
  {
    id: "booking-1003",
    bookingNo: "1003",
    title: "Waghmare Wedding",
    status: "Pending",
    startDate: "26 December 2024",
    endDate: "29 December 2024",
    client: {
      name: "Bandu Waghmare",
      mobile: "7845368678",
      address: "Geeta Nagar"
    },
    events: [
      {
        id: "event-sangeet",
        name: "Sangeet",
        date: "26 December 2024",
        venue: "Geeta Hall",
        lines: [
          { id: "line-1", material: "Laser", quantity: 2, rate: 6500 },
          { id: "line-2", material: "LED Par", quantity: 12, rate: 750 },
          { id: "line-3", material: "Sharpee", quantity: 4, rate: 2500 }
        ]
      },
      {
        id: "event-haldi",
        name: "Haldi",
        date: "27 December 2024",
        venue: "Home Lawn",
        lines: [
          { id: "line-4", material: "LED Par", quantity: 8, rate: 750 },
          { id: "line-5", material: "Other FX Lights", quantity: 1, rate: 8500 }
        ]
      },
      {
        id: "event-saptpadi",
        name: "Saptpadi",
        date: "28 December 2024",
        venue: "Geeta Hall",
        lines: [
          { id: "line-6", material: "Laser", quantity: 1, rate: 6500 },
          { id: "line-7", material: "Sharpee", quantity: 6, rate: 2500 }
        ]
      },
      {
        id: "event-reception",
        name: "Reception",
        date: "29 December 2024",
        venue: "Geeta Hall",
        lines: [
          { id: "line-8", material: "LED Wall", quantity: 1, rate: 30000 },
          { id: "line-9", material: "Sharpee", quantity: 8, rate: 2500 },
          { id: "line-10", material: "Laser", quantity: 2, rate: 6500 }
        ]
      }
    ]
  },
  {
    id: "booking-1004",
    bookingNo: "1004",
    title: "Patil Wedding",
    status: "Pending",
    startDate: "15 January 2025",
    endDate: "17 January 2025",
    client: {
      name: "Rahul Patil",
      mobile: "9876543210",
      address: "Civil Lines"
    },
    events: [
      {
        id: "event-1004-sangeet",
        name: "Sangeet",
        date: "15 January 2025",
        venue: "Lotus Banquet",
        lines: [
          { id: "line-1004-1", material: "Laser", quantity: 2, rate: 6500 },
          { id: "line-1004-2", material: "LED Par", quantity: 10, rate: 750 }
        ]
      },
      {
        id: "event-1004-reception",
        name: "Reception",
        date: "17 January 2025",
        venue: "Lotus Banquet",
        lines: [
          { id: "line-1004-3", material: "LED Wall", quantity: 1, rate: 30000 },
          { id: "line-1004-4", material: "Sharpee", quantity: 5, rate: 2500 }
        ]
      }
    ]
  }
];

// Local fallback material master used by the Add Event Material modal offline.
export const inventoryItems = [
  { id: "item-laser", name: "Laser", category: "FX Light", unit: "Piece", rate: 6500, status: "Active" },
  { id: "item-led-par", name: "LED Par", category: "LED Light", unit: "Piece", rate: 750, status: "Active" },
  { id: "item-led-wall", name: "LED Wall", category: "Display", unit: "Package", rate: 30000, status: "Active" },
  { id: "item-sharpee", name: "Sharpee", category: "Moving Light", unit: "Piece", rate: 2500, status: "Active" },
  { id: "item-fx", name: "Other FX Lights", category: "FX Package", unit: "Package", rate: 8500, status: "Active" }
];

// Local fallback payments used to calculate dashboard/invoice balances offline.
export const payments = [
  { id: "pay-1", bookingId: "booking-1003", amount: 50000, mode: "UPI", date: "20 December 2024" },
  { id: "pay-2", bookingId: "booking-1004", amount: 10000, mode: "Cash", date: "02 January 2025" }
];
