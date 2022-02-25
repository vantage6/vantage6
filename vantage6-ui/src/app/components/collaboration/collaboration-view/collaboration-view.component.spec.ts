import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CollaborationViewComponent } from './collaboration-view.component';

describe('CollaborationViewComponent', () => {
  let component: CollaborationViewComponent;
  let fixture: ComponentFixture<CollaborationViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ CollaborationViewComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(CollaborationViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
