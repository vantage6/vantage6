export interface TableData {
  columns: Column[];
  rows: Row[];
}

interface Column {
  id: string;
  label: string;
}

interface Row {
  id: string;
  columnData: any;
}
