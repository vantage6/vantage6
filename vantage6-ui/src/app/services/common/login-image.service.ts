import { Injectable } from '@angular/core';

let BACKGROUND_IMAGES = [
  'cuppolone.jpg',
  'taipei101.png',
  'trolltunga.jpg',
  // 'harukas2.jpg',
  'petronas.jpg',
];

@Injectable({
  providedIn: 'root',
})
export class LoginImageService {
  background_img = '';

  constructor() {
    this.set();
  }

  private set(): void {
    console.log(this.background_img);
    if (this.background_img === '') {
      // pick random background image
      this.background_img =
        BACKGROUND_IMAGES[Math.floor(Math.random() * BACKGROUND_IMAGES.length)];
    }
  }

  get() {
    return `url('../../../assets/images/login_backgrounds/${this.background_img}')`;
  }
}
