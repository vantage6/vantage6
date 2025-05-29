import { Component, OnInit } from '@angular/core';
import { environment } from 'src/environments/environment';
import { ApiService } from 'src/app/services/api.service';
import { Version } from 'src/app/models/api/version.model';
import packageJson from 'package.json';
import { MatCard, MatCardContent } from '@angular/material/card';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
  imports: [MatCard, MatCardContent]
})
export class HomeComponent implements OnInit {
  serverUrl = environment.server_url;
  uiVersion: string = packageJson.version;
  serverVersion: string = '';

  constructor(private apiService: ApiService) {}

  async ngOnInit(): Promise<void> {
    const result = await this.apiService.getForApi<Version>('/version');
    this.serverVersion = result.version;
  }
}
