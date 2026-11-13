import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/shared/DataTable";

interface SampleItem {
  id: string;
  name: string;
  amount: number;
}

const testColumns: ColumnDef<SampleItem>[] = [
  {
    accessorKey: "name",
    header: "Auditor Name",
    cell: (info) => info.getValue(),
  },
  {
    accessorKey: "amount",
    header: "Disbursed Amount",
    cell: (info) => `₹ ${info.getValue()}`,
  },
];

const testData: SampleItem[] = [
  { id: "1", name: "Vidya Hegde", amount: 50000 },
  { id: "2", name: "Anand Rao", amount: 15000 },
  { id: "3", name: "Suresh Patil", amount: 85000 },
  { id: "4", name: "Ramesh Kumar", amount: 32000 },
  { id: "5", name: "Deepa Nayak", amount: 45000 },
  { id: "6", name: "Chetan Gowda", amount: 92000 },
];

describe("DataTable Component", () => {
  it("renders table headers and row items properly", () => {
    render(<DataTable columns={testColumns} data={testData} initialPageSize={5} />);

    expect(screen.getByText("Auditor Name")).toBeInTheDocument();
    expect(screen.getByText("Disbursed Amount")).toBeInTheDocument();
    expect(screen.getByText("Vidya Hegde")).toBeInTheDocument();
  });

  it("sorts rows ascending and descending when header is clicked", () => {
    render(<DataTable columns={testColumns} data={testData} initialPageSize={10} />);

    const header = screen.getByTestId("column-header-name");

    // Click to sort ascending
    fireEvent.click(header);
    const rowsAsc = screen.getAllByTestId(/^data-row-/);
    expect(rowsAsc[0]).toHaveTextContent("Anand Rao");

    // Click to sort descending
    fireEvent.click(header);
    const rowsDesc = screen.getAllByTestId(/^data-row-/);
    expect(rowsDesc[0]).toHaveTextContent("Vidya Hegde");
  });

  it("handles pagination next and previous controls", () => {
    render(<DataTable columns={testColumns} data={testData} initialPageSize={3} />);

    // Page 1 should show first 3 items
    expect(screen.getByText("Vidya Hegde")).toBeInTheDocument();
    expect(screen.queryByText("Ramesh Kumar")).not.toBeInTheDocument();

    const nextBtn = screen.getByTestId("btn-next-page");
    fireEvent.click(nextBtn);

    // Page 2 should show next items
    expect(screen.getByText("Ramesh Kumar")).toBeInTheDocument();

    const prevBtn = screen.getByTestId("btn-previous-page");
    fireEvent.click(prevBtn);

    // Back to Page 1
    expect(screen.getByText("Vidya Hegde")).toBeInTheDocument();
  });

  it("renders custom empty message when data array is empty", () => {
    render(
      <DataTable
        columns={testColumns}
        data={[]}
        emptyMessage="No audit vouchers found."
      />
    );

    expect(screen.getByTestId("empty-table-message")).toHaveTextContent("No audit vouchers found.");
  });
});
