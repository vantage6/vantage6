import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BaseSingleViewComponent } from './base-single-view.component';

describe('BaseSingleViewComponent', () => {
  let component: BaseSingleViewComponent;
  let fixture: ComponentFixture<BaseSingleViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ BaseSingleViewComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(BaseSingleViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
