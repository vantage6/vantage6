import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Algorithm, AlgorithmForm, ArgumentType } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from './chosen-collaboration.service';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { Pagination } from 'src/app/models/api/pagination.model';
import { ChosenStoreService } from './chosen-store.service';
import { isListTypeArgument } from '../helpers/algorithm.helper';

@Injectable({
  providedIn: 'root'
})
export class AlgorithmService {
  constructor(
    private apiService: ApiService,
    private chosenCollaborationService: ChosenCollaborationService,
    private chosenStoreService: ChosenStoreService
  ) {}

  async getAlgorithms(params: object = {}): Promise<Algorithm[]> {
    const algorithmStores = this.getAlgorithmStoresForCollaboration();
    const results = await Promise.all(
      algorithmStores.map(async (algorithmStore) => {
        return await this.getAlgorithmsForAlgorithmStore(algorithmStore, params);
      })
    );
    // combine the list of lists of algorithms
    return results.reduce((accumulator, val) => accumulator.concat(val), []);
  }

  async getAlgorithmsForAlgorithmStore(algorithmStore: AlgorithmStore, params: object = {}): Promise<Algorithm[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<Algorithm>>(`${algorithmStore.url}`, '/algorithm', {
      per_page: 9999,
      ...params
    });
    const algorithms = result.data;
    // set algorithm store url for each algorithm
    algorithms.forEach((algorithm) => {
      algorithm.algorithm_store_url = algorithmStore.url;
      algorithm.algorithm_store_id = algorithmStore.id;
    });
    return algorithms;
  }

  async getPaginatedAlgorithms(store: AlgorithmStore, currentPage: number, params: object = {}): Promise<Pagination<Algorithm>> {
    const result = await this.apiService.getForAlgorithmApiWithPagination<Algorithm>(store.url, '/algorithm', currentPage, params);
    result.data.forEach((algorithm) => {
      algorithm.algorithm_store_url = store.url;
      algorithm.algorithm_store_id = store.id;
    });
    return result;
  }

  async getAlgorithm(algorithm_store_url: string, id: string): Promise<Algorithm> {
    let result = await this.apiService.getForAlgorithmApi<Algorithm>(algorithm_store_url, `/algorithm/${id}`);

    result.functions.forEach((func) => {
      func.arguments.forEach((arg) => {
        arg.allowed_values = arg.allowed_values?.map((value) => {
          return (value as any).value;
        });
      });
    });

    return result;
  }

  async getAlgorithmByUrl(imageUrl: string, store: AlgorithmStore): Promise<Algorithm | null> {
    const result = await this.getAlgorithmsForAlgorithmStore(store, { image: imageUrl });
    // const result = await this.getAlgorithmsForAlgorithmStore(store, { image: imageUrl });
    if (result.length === 0) {
      return null;
    }
    return result[0];
  }

  async createAlgorithm(algorithm: AlgorithmForm): Promise<Algorithm | undefined> {
    algorithm = this.cleanAlgorithmForm(algorithm);
    const algorithmStore = this.chosenStoreService.store$.value;
    if (!algorithmStore) return;
    const result = await this.apiService.postForAlgorithmApi<Algorithm>(algorithmStore.url, '/algorithm', algorithm);
    return result;
  }

  async editAlgorithm(algorithmId: string, algorithm: AlgorithmForm): Promise<Algorithm | undefined> {
    algorithm = this.cleanAlgorithmForm(algorithm);
    const algorithmStore = this.chosenStoreService.store$.value;
    if (!algorithmStore) return;
    const result = await this.apiService.patchForAlgorithmApi<Algorithm>(algorithmStore.url, `/algorithm/${algorithmId}`, algorithm);
    return result;
  }

  async deleteAlgorithm(algorithmId: string): Promise<void> {
    const algorithmStore = this.chosenStoreService.store$.value;
    if (!algorithmStore) return;
    return await this.apiService.deleteForAlgorithmApi(algorithmStore.url, `/algorithm/${algorithmId}`);
  }

  async invalidateAlgorithm(algorithmId: string): Promise<void> {
    const algorithmStore = this.chosenStoreService.store$.value;
    if (!algorithmStore) return;
    return await this.apiService.postForAlgorithmApi(algorithmStore.url, `/algorithm/${algorithmId}/invalidate`, {});
  }

  private getAlgorithmStoresForCollaboration(): AlgorithmStore[] {
    const collaboration = this.chosenCollaborationService.collaboration$.getValue();
    if (!collaboration) {
      return [];
    }
    return collaboration.algorithm_stores;
  }

  private cleanAlgorithmForm(algorithmForm: AlgorithmForm): AlgorithmForm {
    algorithmForm.functions.forEach((func) => {
      func.arguments.forEach((arg) => {
        // remove the parameter's 'default_value_type' fields - they are only needed to
        // acquire a correct value in the UI but are not needed for the backend
        // also cast the 'has_default_value' field to a boolean, in the HTML it is a string.
        arg.has_default_value = arg.has_default_value === 'true' || arg.has_default_value === true;
        arg.is_frontend_only = arg.is_frontend_only === 'true' || arg.is_frontend_only === true;
        if (arg.is_default_value_null === true) {
          delete arg.default_value;
        } else if (isListTypeArgument(arg.type) && arg.default_value) {
          // if the argument is a list type, parse the comma-separated string to an
          // array of the right type
          arg.default_value = (arg.default_value as string).split(',');
          if (arg.type === ArgumentType.FloatList) {
            arg.default_value = JSON.stringify(
              arg.default_value.map((val) => {
                return Number.parseFloat(val);
              })
            );
          } else if (arg.type === ArgumentType.IntegerList || arg.type === ArgumentType.OrganizationList) {
            arg.default_value = JSON.stringify(
              arg.default_value.map((val) => {
                return Number.parseInt(val);
              })
            );
          } else {
            arg.default_value = JSON.stringify(arg.default_value);
          }
        }
        delete arg.is_default_value_null;
        // similarly, clean up the conditional argument fields
        delete arg.hasCondition;
        // Note: we do NOT check the conditional value and operator here. It is checked
        // in the form that they are either all or none defined. Checking the
        // conditional_value may also be more complex as it may be 'false'.
        if (!arg.conditional_on) {
          delete arg.conditional_on;
          delete arg.conditional_operator;
          delete arg.conditional_value;
        }
        if (arg.conditional_value || arg.conditional_value === false) {
          // cast to string as it is stored as string in the database
          arg.conditional_value = arg.conditional_value.toString();
        }
      });
    });
    return algorithmForm;
  }
}
