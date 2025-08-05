/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchRequest } from 'src/app/components/table/table.component';
import { Pagination } from 'src/app/models/api/pagination.model';
import { ApiService } from 'src/app/services/api.service';
import { AlgorithmStore } from '../models/api/algorithmStore.model';

export const getLazyProperties = async (
  result: any,
  data: any,
  lazyProperties: string[],
  apiService: ApiService,
  algoStore: AlgorithmStore | null = null
): Promise<void> => {
  await Promise.all(
    lazyProperties.map(async (lazyProperty) => {
      if (!result[lazyProperty]) return;

      // eslint-disable-next-line no-prototype-builtins
      if (result[lazyProperty].hasOwnProperty('link') && result[lazyProperty].link) {
        let resultProperty;
        if (algoStore === null) {
          resultProperty = await apiService.getForApi<any>((result as any)[lazyProperty].link);
        } else if (algoStore !== null) {
          resultProperty = await apiService.getForAlgorithmApi<any>(algoStore, (result as any)[lazyProperty].link);
        }
        data[lazyProperty] = resultProperty;
      } else {
        let resultProperty;
        if (algoStore === null) {
          resultProperty = await apiService.getForApi<Pagination<any>>(result[lazyProperty], { per_page: 9999 });
        } else {
          resultProperty = await apiService.getForAlgorithmApi<Pagination<any>>(algoStore, result[lazyProperty], { per_page: 9999 });
        }
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
