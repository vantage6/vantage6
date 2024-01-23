/* eslint-disable @typescript-eslint/no-explicit-any */
import { EnvironmentConfig } from 'src/app/models/application/enivronmentConfig.model';

const env: EnvironmentConfig = {
  production: true,
  server_url: (window as any).env?.server_url || 'https://cotopaxi.vantage6.ai',
  api_path: (window as any).env?.api_path || '',
  version: '0.0.0'
};

export const environment = env;
