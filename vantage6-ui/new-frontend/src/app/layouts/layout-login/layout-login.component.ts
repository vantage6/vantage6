import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-layout-login',
  templateUrl: './layout-login.component.html',
  styleUrls: ['./layout-login.component.scss']
})
export class LayoutLoginComponent implements OnInit {
  backgroundUrl: string = '';

  ngOnInit(): void {
    const backgroundNumber = Math.floor(Math.random() * 4) + 1;
    this.backgroundUrl = `url(assets/images/login_backgrounds/${backgroundNumber}.jpg)`;
  }
}
