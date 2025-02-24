import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ReviewSubmitComponent } from './review-submit.component';

describe('ReviewSubmitComponent', () => {
  let component: ReviewSubmitComponent;
  let fixture: ComponentFixture<ReviewSubmitComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReviewSubmitComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ReviewSubmitComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
