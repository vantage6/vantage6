import { Component, OnInit } from '@angular/core';
import { environment } from 'src/environments/environment';
import packageJson from '../../../../package.json';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {
  api_url = environment.api_url;
  public version: string = packageJson.version;

  constructor() {}

  ngOnInit() {}
}
