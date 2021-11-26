import { Component, OnInit } from '@angular/core';

import { TokenStorageService } from '../services/token-storage.service';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {
  permissions: string[] = [];

  constructor(private tokenStorage: TokenStorageService) {}

  ngOnInit() {
    this.tokenStorage.getUserRules().subscribe((rules: string[]) => {
      this.permissions = rules;
    });
  }
}
