/* eslint-disable @typescript-eslint/no-explicit-any */
import { EnvironmentConfig } from 'src/app/models/application/enivronmentConfig.model';

const env: EnvironmentConfig = {
  production: true,
  server_url: (window as any).env?.server_url || 'https://cotopaxi.vantage6.ai',
  api_path: (window as any).env?.api_path || '',
  community_store_url: (window as any).env?.community_store_url || 'https://store.cotopaxi.vantage6.ai/api'
};

export const environment = env;
