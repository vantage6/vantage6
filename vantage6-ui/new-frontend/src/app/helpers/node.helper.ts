import { BaseNode, Database, DatabaseType } from '../models/api/node.model';

export const getDatabasesFromNode = (node: BaseNode): Database[] => {
  const databaseNames: string[] = [];

  node.config.forEach((config) => {
    if (config.key.startsWith('database_')) {
      databaseNames.push(config.value);
    }
  });

  const databases: Database[] = databaseNames.map((name) => {
    const type = node.config.find((config) => config.key === `db_type_${name}`)?.value;
    return {
      name,
      type: type || DatabaseType.Other
    } as Database;
  });

  return databases;
};
