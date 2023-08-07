import { Component } from '@angular/core';
import { environment } from 'src/environments/environment';
import { ApiService } from '../../services/api.service';
import { Version } from '../../models/api/version.model';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent {
  serverUrl = environment.server_url;
  uiVersion: string = environment.version;
  serverVersion: string = '';

  constructor(private apiService: ApiService) {}

  async ngOnInit(): Promise<void> {
    const result = await this.apiService.get<Version>(this.serverUrl + '/version');
    this.serverVersion = result.version;
  }
}
