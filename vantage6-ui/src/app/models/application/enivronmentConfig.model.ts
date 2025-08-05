export interface EnvironmentConfig {
  production: boolean;
  server_url: string;
  api_path: string;
  auth_url: string;
  keycloak_realm: string;
  keycloak_client: string;
  refresh_token_validity_seconds: number;
  community_store_url: string;
  community_store_api_path: string;
}
