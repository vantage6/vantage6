export interface EnvironmentConfig {
  production: boolean;
  server_url: string;
  api_path: string;
  auth_url: string;
  keycloak_realm: string;
  keycloak_client: string;
}
