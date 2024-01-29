export interface TableData {
  columns: Column[];
  rows: Row[];
}

export interface Column {
  id: string;
  label: string;
  searchEnabled?: boolean;
  initSearchString?: string;
  filterEnabled?: boolean;
  isChip?: boolean;
  chipTypeProperty?: string;
}

interface Row {
  id: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columnData: any;
}
