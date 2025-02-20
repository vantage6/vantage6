import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OldAlgorithmListComponent } from './old-algorithm-list.component';

describe('OldAlgorithmListComponent', () => {
  let component: OldAlgorithmListComponent;
  let fixture: ComponentFixture<OldAlgorithmListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OldAlgorithmListComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(OldAlgorithmListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
