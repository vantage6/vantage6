import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-layout-login',
  templateUrl: './layout-login.component.html',
  styleUrls: ['./layout-login.component.scss']
})
export class LayoutLoginComponent implements OnInit {
  background_img_data: any = null;
  backgroundUrl: string = '';

  BACKGROUND_IMAGES = [
    {
      'image': 'cuppolone',
    },
    {
      'image': 'taipei101',
    },
    {
      'image': 'trolltunga',
      'additional_styling': {'background-position-y': 'top'},
      'attribution': 'Trolltunga, Norway by <a href="https://web.archive.org/web/20161102185545/http://www.panoramio.com/user/5226993?with_photo_id=119985909">rheins</a> (License CC BY 3.0)'
    },
    // {
    //   'image': 'harukas2',
    // },
    {
      'image': 'petronas',
    },
    {
      'image': 'cotopaxi',
      'additional_styling': {'background-position-y': 'top'},
      'attribution': 'Cotopaxi, Ecuador by <a href="https://www.flickr.com/people/16448758@N03">Rinaldo Wurglitsch</a> (License CC BY 2.0)'
    },
  ];

  ngOnInit(): void {
    this.background_img_data = this.BACKGROUND_IMAGES[Math.floor(Math.random() * this.BACKGROUND_IMAGES.length)];
    this.backgroundUrl = `url(assets/images/login_backgrounds/${this.background_img_data['image']}.jpg)`;
  }

  getBackgroundStyle() {
    let style: any = this.getAdditionalStyling();
    style['background-image'] = this.backgroundUrl;
    return style;
  }

  getAdditionalStyling() {
    if ('additional_styling' in this.background_img_data){
      return this.background_img_data['additional_styling'];
    }
    return {};
  }

  getAttributionText() {
    if ('attribution' in this.background_img_data){
      return this.background_img_data['attribution'];
    }
    return '';
  }
}
