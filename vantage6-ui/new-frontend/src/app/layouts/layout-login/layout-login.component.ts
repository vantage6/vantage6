import { Component, OnInit } from '@angular/core';

interface BackgroundImage {
  image: string;
  additional_styling?: object;
  attribution?: string;
}

@Component({
  selector: 'app-layout-login',
  templateUrl: './layout-login.component.html',
  styleUrls: ['./layout-login.component.scss']
})
export class LayoutLoginComponent implements OnInit {
  backgroundImage: BackgroundImage | null = null;
  backgroundUrl: string = '';

  BACKGROUND_IMAGES = [
    {
      image: 'cuppolone'
    },
    {
      image: 'taipei'
    },
    {
      image: 'trolltunga',
      additional_styling: { 'background-position-y': 'top' },
      attribution:
        'Trolltunga, Norway by <a href="https://web.archive.org/web/20161102185545/http://www.panoramio.com/user/5226993?with_photo_id=119985909">rheins</a> (License CC BY 3.0)'
    },
    {
      image: 'petronas'
    },
    {
      image: 'cotopaxi',
      additional_styling: { 'background-position-y': 'top' },
      attribution: 'Cotopaxi, Ecuador by <a href="https://www.flickr.com/people/16448758@N03">Rinaldo Wurglitsch</a> (License CC BY 2.0)'
    }
  ];

  ngOnInit(): void {
    this.backgroundImage = this.BACKGROUND_IMAGES[Math.floor(Math.random() * this.BACKGROUND_IMAGES.length)];
    this.backgroundUrl = `url(assets/images/login_backgrounds/${this.backgroundImage.image}.jpg)`;
  }

  get backgroundStyle(): object {
    let style = {
      'background-image': this.backgroundUrl
    };
    if (this.backgroundImage?.additional_styling) {
      style = { ...style, ...this.backgroundImage.additional_styling };
    }

    return style;
  }

  get attributionText(): string | null {
    return this.backgroundImage?.attribution || null;
  }
}
