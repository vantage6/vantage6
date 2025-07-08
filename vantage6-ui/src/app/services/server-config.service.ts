import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { ServerConfig } from 'src/app/models/api/server-config.model';

@Injectable({
  providedIn: 'root'
})
export class ServerConfigService {
  isInitialized: boolean = false;
  keycloakConfig: ServerConfig | null = null;

  constructor(private apiService: ApiService) {
    this.init();
  }

  async init() {
    this.keycloakConfig = await this.getKeycloakConfig();
    console.log('keycloakConfig', this.keycloakConfig);
    this.isInitialized = true;
  }

  async doesKeycloakManageUsersAndNodes(): Promise<boolean> {
    if (!this.isInitialized) {
      await this.init();
    }
    return this.keycloakConfig?.manage_users_and_nodes ?? false;
  }

  /**
   * Get server configuration from the /server_config/keycloak endpoint
   * @returns Promise<ServerConfig> - The server configuration data
   */
  private async getKeycloakConfig(): Promise<ServerConfig> {
    return await this.apiService.getForApi<ServerConfig>('/server_config/keycloak');
  }
}
