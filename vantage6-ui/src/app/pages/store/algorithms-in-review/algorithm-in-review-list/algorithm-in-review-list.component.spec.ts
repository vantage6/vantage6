import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmInReviewListComponent } from './algorithm-in-review-list.component';

describe('AlgorithmInReviewListComponent', () => {
  let component: AlgorithmInReviewListComponent;
  let fixture: ComponentFixture<AlgorithmInReviewListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlgorithmInReviewListComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AlgorithmInReviewListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
