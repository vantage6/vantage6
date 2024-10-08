// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function parseDefaultPandasFormat(
  df: { [key: string]: any[] },
  parameterTxt: string,
  columns: string[] | null
): { columns: string[]; rows: any[] } {
  if (!columns) {
    columns = Object.keys(df);
  }
  const indices = Object.keys(Object.values(df)[0]);
  const rows: any = [];
  // if the indices are not simply numbers, add them as first row
  const indices_are_numbers: boolean = indices[0] !== '0';
  if (indices_are_numbers) {
    // add extra column for indices
    columns = [parameterTxt, ...columns];
  }
  indices.forEach((index: any) => {
    const row: any = {};
    for (const column of columns) {
      if (column === parameterTxt) {
        row[parameterTxt] = index;
      } else {
        row[column] = df[column][index] as string;
      }
    }
    rows.push(row);
  });
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
