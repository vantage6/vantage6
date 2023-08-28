import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ChipComponent } from './chip.component';

describe('ChipComponent', () => {
  let component: ChipComponent;
  let fixture: ComponentFixture<ChipComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [ChipComponent]
    });
    fixture = TestBed.createComponent(ChipComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
