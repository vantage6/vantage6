// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function parseDefaultPandasFormat(df: { [key: string]: any[] }, columns: string[] | null): { columns: string[]; rows: any } {
  if (!columns) {
    columns = Object.keys(df);
  }
  const rows = [];
  for (let i = 0; i < Object.keys(Object.values(df)[0]).length; i++) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const row: any = {};
    for (const column of columns) {
      row[column] = df[column][i] as string;
    }
    rows.push(row);
  }
  return { columns: columns, rows: rows };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function parseRecordsFormat(df: any, columns: string[] | null): { columns: string[]; rows: any } {
  // if the result is a single table row, convert it to an array of rows
  if (!Array.isArray(df)) {
    df = [df];
  }

  if (!columns) {
    columns = Object.keys(df[0]);
  }
  const rows = df;

  return { columns: columns, rows: rows };
}
