import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ReviewReadComponent } from './review-read.component';

describe('ReviewReadComponent', () => {
  let component: ReviewReadComponent;
  let fixture: ComponentFixture<ReviewReadComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReviewReadComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ReviewReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
