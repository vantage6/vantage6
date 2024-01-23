/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchRequest } from '../components/table/table.component';
import { Pagination } from '../models/api/pagination.model';
import { ApiService } from '../services/api.service';

export const getLazyProperties = async (result: any, data: any, lazyProperties: string[], apiService: ApiService): Promise<void> => {
  await Promise.all(
    lazyProperties.map(async (lazyProperty) => {
      if (!result[lazyProperty]) return;

      // eslint-disable-next-line no-prototype-builtins
      if (result[lazyProperty].hasOwnProperty('link') && result[lazyProperty].link) {
        const resultProperty = await apiService.getForApi<any>((result as any)[lazyProperty].link);
        data[lazyProperty] = resultProperty;
      } else {
        const resultProperty = await apiService.getForApi<Pagination<any>>(result[lazyProperty]);
        data[lazyProperty] = resultProperty.data;
      }
    })
  );
};

export const getApiSearchParameters = function <T>(searchRequests?: SearchRequest[]): T {
  if (!searchRequests) return {} as T;

  const parameters: T = {} as T;
  searchRequests.forEach((request) => {
    if (request.searchString?.trim().length > 0) {
      const key = request.columnId as keyof typeof parameters;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      parameters[key] = `%${request.searchString}%` as any;
    }
  });
  return parameters;
};
