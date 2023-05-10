export interface Pagination {
  all_pages: boolean;
  page?: number;
  page_size?: number;
  collaboration_id?: number;
  organization_id?: number;
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

export function getPageId(page: Pagination) {
  let page_id = page.all_pages ? 'all' : 'page';
  page_id += `_${page.page}_${page.page_size}`;
  if (page.collaboration_id) {
    page_id += `_col_${page.collaboration_id}`;
  }
  if (page.organization_id) page_id += `_org_${page.organization_id}`;
  return page_id;
}

export function getPageSize(page_id: string): number {
  return parseInt(page_id.split('_')[2]);
}
