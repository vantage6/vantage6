export interface Pagination {
  all_pages: boolean;
  page?: number;
  page_size?: number;
}

export function allPages(): Pagination {
  return { all_pages: true };
}

export function defaultFirstPage(): Pagination {
  return {
    all_pages: false,
    page: 1,
    page_size: 10,
  };
}
