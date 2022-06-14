import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CollaborationViewSingleComponent } from './collaboration-view-single.component';

describe('CollaborationViewSingleComponent', () => {
  let component: CollaborationViewSingleComponent;
  let fixture: ComponentFixture<CollaborationViewSingleComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ CollaborationViewSingleComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(CollaborationViewSingleComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
