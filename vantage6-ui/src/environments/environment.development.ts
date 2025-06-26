import { EnvironmentConfig } from 'src/app/models/application/enivronmentConfig.model';

const env: EnvironmentConfig = {
  production: false,
  // server_url: 'https://cotopaxi.vantage6.ai',
  // api_path: ''
  server_url: (window as any).env?.server_url || 'http://localhost:7601',
  api_path: (window as any).env?.api_path || '/server',
  auth_url: (window as any).env?.auth_url || 'http://localhost:8080',
  keycloak_realm: (window as any).env?.keycloak_realm || 'vantage6',
  keycloak_client: (window as any).env?.keycloak_client || 'public_client'
};

export const environment = env;
