import { EnvironmentConfig } from 'src/app/models/application/enivronmentConfig.model';

const env: EnvironmentConfig = {
  production: false,
  // server_url: 'https://cotopaxi.vantage6.ai',
  // api_path: ''
  server_url: 'http://localhost:7601',
  api_path: '/server',
  auth_url: 'http://localhost:8080',
  keycloak_realm: 'vantage6',
  keycloak_client: 'public_client'
};

export const environment = env;
