import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class LoginImageService {
  background_img: any = null;

  BACKGROUND_IMAGES = [
    {
      'image': 'cuppolone.jpg',
    },
    {
      'image': 'taipei101.png',
    },
    {
      'image': 'trolltunga.jpg',
    },
    {
      'image': 'harukas2.jpg',
    },
    {
      'image': 'petronas.jpg',
    },
    {
      'image': 'cotopaxi.jpg',
      'additional_styling': 'background-position-y: top;',
      'attribution': 'Cotopaxi, Ecuador by <a href="https://www.flickr.com/people/16448758@N03">Rinaldo Wurglitsch</a> (LicenseCC BY 2.0)'
    },
  ];

  constructor() {
    this.set();
  }

  private set(): void {
    if (this.background_img === null) {
      // pick random background image
      this.background_img =
        this.BACKGROUND_IMAGES[Math.floor(Math.random() * this.BACKGROUND_IMAGES.length)];
    }
  }

  get() {
    return `url('../../../assets/images/login_backgrounds/${this.background_img['image']}')`;
  }

  getAdditionalStyling() {
    if ('additional_styling' in this.background_img){
      return this.background_img['additional_styling'];
    }
    return '';
  }

  getAttributionText() {
    if ('attribution' in this.background_img){
      return this.background_img['attribution'];
    }
    return '';
  }
}
