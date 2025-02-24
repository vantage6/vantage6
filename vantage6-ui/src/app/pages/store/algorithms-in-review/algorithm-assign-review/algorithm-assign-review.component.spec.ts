import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmAssignReviewComponent } from './algorithm-assign-review.component';

describe('AlgorithmAssignReviewComponent', () => {
  let component: AlgorithmAssignReviewComponent;
  let fixture: ComponentFixture<AlgorithmAssignReviewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlgorithmAssignReviewComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AlgorithmAssignReviewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
