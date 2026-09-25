export interface Column<T> {
  header: string;
  render: (row: T) => React.ReactNode;
  key: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyMessage?: string;
}

export default function Table<T>({ columns, rows, rowKey, emptyMessage = "Nothing here yet." }: TableProps<T>) {
  if (rows.length === 0) {
    return <p className="empty-message">{emptyMessage}</p>;
  }
  return (
    <table className="table">
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={col.key}>{col.header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={rowKey(row)}>
            {columns.map((col) => (
              <td key={col.key}>{col.render(row)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
