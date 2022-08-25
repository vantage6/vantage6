import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

let BACKGROUND_IMAGES = [
  'cuppolone.jpg',
  'taipei101.png',
  'trolltunga.jpg',
  // 'harukas2.jpg',
  'petronas.jpg',
];

@Component({
  selector: 'app-login-page',
  templateUrl: './login-page.component.html',
  styleUrls: ['./login-page.component.scss'],
})
export class LoginPageComponent implements OnInit {
  background_img = '';

  constructor(public router: Router) {}

  ngOnInit(): void {
    this.background_img = this._pickBackgroundImage();
  }

  private _pickBackgroundImage(): string {
    // pick random background image
    return BACKGROUND_IMAGES[
      Math.floor(Math.random() * BACKGROUND_IMAGES.length)
    ];
  }

  _getBackgroundImage() {
    return `url('../../../../assets/images/login_backgrounds/${this.background_img}')`;
  }
}
