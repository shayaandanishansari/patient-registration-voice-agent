import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";

import type { Patient } from "../types";
import { PatientProfile } from "./PatientProfile";
import { PatientTable } from "./PatientTable";

const patient: Patient = {
  patient_id: "p-1",
  member_id: "08803337",
  first_name: "Jane",
  last_name: "Doe",
  date_of_birth: "1990-03-05",
  sex: "Female",
  phone_number: "5125550123",
  email: null,
  address_line_1: "123 Main St",
  address_line_2: "Apt 4B",
  city: "Austin",
  state: "TX",
  zip_code: "78701",
  insurance_provider: "Aetna",
  insurance_member_id: "W123456",
  preferred_language: "Spanish",
  emergency_contact_name: null,
  emergency_contact_phone: null,
  created_at: "2026-09-24T00:00:00+00:00",
  updated_at: "2026-09-24T00:00:00+00:00",
  created_via: "voice",
};

describe("PatientTable", () => {
  it("opens the patient when anywhere on the row is clicked", async () => {
    const router = createMemoryRouter(
      [
        { path: "/patients", element: <PatientTable patients={[patient]} /> },
        { path: "/patients/:id", element: <p>detail page</p> },
      ],
      { initialEntries: ["/patients"] },
    );
    render(<RouterProvider router={router} />);

    await userEvent.click(screen.getByText("Austin, TX"));

    expect(await screen.findByText("detail page")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/patients/p-1");
  });

  it("marks only the records flagged as possible duplicates", () => {
    const other = { ...patient, patient_id: "p-2", first_name: "John" };
    const router = createMemoryRouter(
      [
        {
          path: "/patients",
          element: <PatientTable patients={[patient, other]} duplicateIds={new Set(["p-1"])} />,
        },
      ],
      { initialEntries: ["/patients"] },
    );
    render(<RouterProvider router={router} />);

    const badges = screen.getAllByText("Possible duplicate");
    expect(badges).toHaveLength(1);
    expect(badges[0].closest("tr")).toHaveTextContent("Doe, Jane");
  });
});

describe("PatientProfile", () => {
  it("shows the optional fields, and says when one wasn't given", () => {
    render(<PatientProfile patient={patient} />);

    expect(screen.getByText("Aetna")).toBeInTheDocument();
    expect(screen.getByText("W123456")).toBeInTheDocument();
    expect(screen.getByText("Spanish")).toBeInTheDocument();
    expect(screen.getByText("123 Main St, Apt 4B, Austin, TX 78701")).toBeInTheDocument();
    // email, emergency contact name and phone were not given
    expect(screen.getAllByText("Not provided")).toHaveLength(3);
  });
});
