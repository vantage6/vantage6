import { Algorithm } from 'src/app/models/api/algorithm.model';
import { StoreUser } from 'src/app/models/api/store-user.model';

export function assignDevelopersToAlgorithms(algorithms: Algorithm[], storeUsers: StoreUser[]): Algorithm[] {
  algorithms.forEach((algorithm) => {
    const user = storeUsers.find((storeUser) => storeUser.id === algorithm.developer_id);
    algorithm.developer = user ? user : undefined;
  });
  return algorithms;
}
