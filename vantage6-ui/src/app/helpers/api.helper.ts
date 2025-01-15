/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchRequest } from 'src/app/components/table/table.component';
import { Pagination } from 'src/app/models/api/pagination.model';
import { ApiService } from 'src/app/services/api.service';

export const getLazyProperties = async (
  result: any,
  data: any,
  lazyProperties: string[],
  apiService: ApiService,
  algo_store_url: string | null = null
): Promise<void> => {
  await Promise.all(
    lazyProperties.map(async (lazyProperty) => {
      if (!result[lazyProperty]) return;

      // eslint-disable-next-line no-prototype-builtins
      if (result[lazyProperty].hasOwnProperty('link') && result[lazyProperty].link) {
        let resultProperty;
        if (algo_store_url === null) {
          resultProperty = await apiService.getForApi<any>((result as any)[lazyProperty].link);
        } else if (algo_store_url !== null) {
          const cleanApiLink = removeAPIPathFromLink((result as any)[lazyProperty].link, algo_store_url);
          resultProperty = await apiService.getForAlgorithmApi<any>(algo_store_url, cleanApiLink);
        }
        data[lazyProperty] = resultProperty;
      } else {
        let resultProperty;
        if (algo_store_url === null) {
          resultProperty = await apiService.getForApi<Pagination<any>>(result[lazyProperty], { per_page: 9999 });
        } else {
          // TODO we have double API Path here - we need to fix it. Now we find API path but this is wonky
          const cleanApiLink = removeAPIPathFromLink(result[lazyProperty], algo_store_url);
          resultProperty = await apiService.getForAlgorithmApi<Pagination<any>>(algo_store_url, cleanApiLink, { per_page: 9999 });
        }
        data[lazyProperty] = resultProperty.data;
      }
    })
  );
};

function removeAPIPathFromLink(apiLink: string, storeUrl: string): string {
  const apiPath = findAPIPath(storeUrl, apiLink);
  return apiLink.replace(apiPath, '');
}

// this is used to find the API path. It checks that if store URL is some-url/apipath, and the API link is
// /apipath/role/1, that '/apipath' is the API path by finding max common substring.
function findAPIPath(storeUrl: string, apiLink: string): string {
  let maxSubstring = '';

  // Iterate over substrings of decreasing length from the start of str1
  for (let i = 0; i < apiLink.length; i++) {
    const substring = apiLink.substring(0, apiLink.length - i);
    if (storeUrl.endsWith(substring)) {
      maxSubstring = substring;
      break; // Found the longest match, no need to check shorter substrings
    }
  }

  return maxSubstring;
}

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
