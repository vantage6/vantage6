import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CollaborationReadComponent } from './collaboration-read.component';

describe('CollaborationReadComponent', () => {
  let component: CollaborationReadComponent;
  let fixture: ComponentFixture<CollaborationReadComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [CollaborationReadComponent]
    });
    fixture = TestBed.createComponent(CollaborationReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
