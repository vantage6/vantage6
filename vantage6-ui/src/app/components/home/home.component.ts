import { Component, OnInit } from '@angular/core';
import { environment } from 'src/environments/environment';
import packageJson from '../../../../package.json';
import { VersionApiService } from 'src/app/services/api/version-api.service';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {
  api_url = environment.api_url;
  public version: string = packageJson.version;
  public server_version: string = '';

  constructor(
    private versionApiService: VersionApiService
  ) {}

  ngOnInit() {
    this.getServerVersion();
  }

  async getServerVersion() {
    this.server_version = await this.versionApiService.getVersion();
  }
}
