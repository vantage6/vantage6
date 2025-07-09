/* eslint-disable @typescript-eslint/no-explicit-any */
import { EnvironmentConfig } from 'src/app/models/application/enivronmentConfig.model';

const env: EnvironmentConfig = {
  production: true,
  server_url: (window as any).env?.server_url || 'https://cotopaxi.vantage6.ai',
  api_path: (window as any).env?.api_path || '',
  auth_url: (window as any).env?.auth_url || 'https://auth.cotopaxi.vantage6.ai',
  keycloak_realm: (window as any).env?.keycloak_realm || 'vantage6',
  keycloak_client: (window as any).env?.keycloak_client || 'public_client',
  community_store_url: (window as any).env?.community_store_url || 'https://store.cotopaxi.vantage6.ai/api'
};

export const environment = env;
